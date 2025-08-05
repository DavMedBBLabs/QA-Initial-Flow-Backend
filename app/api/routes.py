from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from datetime import datetime, timezone

from ..database.connection import get_db
from ..database.models import HU, HUStatus, User, Project
from ..schemas.hu_schemas import HUCreate, HUStatusUpdate, HUResponse, TestGenerationRequest
from ..auth.schemas import ProjectCreate, ProjectResponse, ProjectListResponse, ProjectUpdate
from ..auth.jwt import get_current_active_user, verify_password
from ..services.azure_service import AzureService
from ..services.deepseek_service import DeepSeekService
from ..services.xray_service import XRayService

# Helper function
def hu_to_dict(hu: HU) -> dict:
    # Mapear el estado correctamente desde el enum
    status_mapping = {
        'ACCEPTED': 'accepted',
        'PENDING': 'pending',
        'REJECTED': 'rejected'
    }
    
    # Obtener el valor del enum
    status_value = hu.status.value if hasattr(hu.status, 'value') else str(hu.status)
    
    return {
        "id": str(hu.id),
        "azure_id": hu.azure_id,
        "name": hu.name,
        "description": hu.description,
        "status": status_mapping.get(status_value, status_value.lower()),
        "refined_response": hu.refined_response,  # Campo requerido por el schema
        "markdown_response": hu.markdown_response,  # Campo requerido por el schema
        "feature": hu.feature,
        "module": hu.module,
        "language": hu.language or 'es',  # Campo de idioma
        "created_at": hu.created_at.isoformat() if hu.created_at else None,
        "updated_at": hu.updated_at.isoformat() if hu.updated_at else None
    }

def get_azure_service_for_user(current_user: User, db: Session) -> AzureService:
    """
    Obtiene el AzureService configurado con las credenciales del proyecto activo del usuario
    """
    
    # Buscar el proyecto activo del usuario
    active_project = db.query(Project).filter(
        Project.user_id == current_user.id,
        Project.is_active == True
    ).first()
    
    if not active_project:
        raise HTTPException(
            status_code=400, 
            detail="No hay proyecto activo. Por favor, crea o selecciona un proyecto primero."
        )
    
    # Crear AzureService con las credenciales del proyecto activo
    azure_service = AzureService()
    azure_service.token = active_project.azure_devops_token
    azure_service.org = active_project.azure_org
    azure_service.project = active_project.azure_project
    azure_service.headers = {
        "Authorization": f"Bearer {active_project.azure_devops_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    return azure_service

def get_xray_service_for_user(current_user: User, db: Session) -> XRayService:
    """
    Obtiene el XRayService configurado con las credenciales del proyecto activo del usuario
    """
    # Buscar el proyecto activo del usuario
    active_project = db.query(Project).filter(
        Project.user_id == current_user.id,
        Project.is_active == True
    ).first()
    
    if not active_project:
        raise HTTPException(
            status_code=400, 
            detail="No hay proyecto activo. Por favor, crea o selecciona un proyecto primero."
        )
    
    # Crear XRayService con las credenciales del proyecto activo
    xray_service = XRayService()
    xray_service.client_id = active_project.client_id
    xray_service.client_secret = active_project.client_secret
    
    return xray_service

def create_hu_endpoint(
    hu_data: HUCreate, 
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        # Debug: Imprimir los datos recibidos
        print(f"🔍 DEBUG: Datos recibidos en create_hu_endpoint:")
        print(f"   📝 azure_id: {hu_data.azure_id}")
        print(f"   🌐 language: {hu_data.language}")
        print(f"   👤 usuario: {current_user.username}")
        
        # Check if exists
        existing = db.query(HU).filter(HU.azure_id == hu_data.azure_id).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"HU {hu_data.azure_id} already exists")
        
        # ✅ Obtener proyecto activo del usuario
        active_project = db.query(Project).filter(
            Project.user_id == current_user.id,
            Project.is_active == True
        ).first()
        
        if not active_project:
            raise HTTPException(status_code=400, detail="No hay proyecto activo. Por favor, crea o selecciona un proyecto primero.")
        
        # ✅ MEJORADO: Obtener AzureService con credenciales del proyecto activo
        azure_service = get_azure_service_for_user(current_user, db)
        
        # ✅ MEJORADO: Fetch con información más completa
        azure_data = azure_service.fetch_hu(hu_data.azure_id)
        
        # Create HU immediately with basic data and project assignment
        new_hu = HU(
            azure_id=hu_data.azure_id,
            name=azure_data['title'],
            description=azure_data['description'],
            refined_response="🤖 Refinando con IA... Por favor espera.",
            markdown_response="🤖 Refinando con IA... Por favor espera.",
            feature=azure_data.get('feature'),
            module=azure_data.get('module'),
            language=hu_data.language or 'es',  # Usar el idioma seleccionado
            project_id=active_project.id  # ✅ Asignar proyecto activo
        )
        
        print(f"🔍 DEBUG: Creando HU con idioma: {new_hu.language}")
        
        db.add(new_hu)
        db.commit()
        db.refresh(new_hu)
        
        # ✅ MEJORADO: Refinamiento con información adicional y idioma
        try:
            print(f"🔍 DEBUG: Iniciando refinamiento con idioma: {hu_data.language or 'es'}")
            gemma_service = DeepSeekService()
            refined_text, markdown_text = gemma_service.refine_hu(
                azure_data.get('title', ''), 
                azure_data.get('description', ''), 
                azure_data.get('acceptanceCriteria', ''),
                azure_data.get('feature', ''),
                azure_data.get('module', ''),
                hu_data.language or 'es'  # Pasar el idioma al servicio
            )
            
            print(f"🔍 DEBUG: Refinamiento completado. Longitud del texto: {len(refined_text)}")
            
            # Update with refined content
            new_hu.refined_response = refined_text
            new_hu.markdown_response = markdown_text
            db.commit()
            db.refresh(new_hu)
            
        except Exception as ai_error:
            print(f"❌ Error durante refinamiento: {str(ai_error)}")
            new_hu.refined_response = f"❌ Error refinando: {str(ai_error)}"
            new_hu.markdown_response = f"❌ Error refinando: {str(ai_error)}"
            db.commit()
            db.refresh(new_hu)
        
        return hu_to_dict(new_hu)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creating HU: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error al procesar la HU: {str(e)}")

def get_hus_endpoint(
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    name: Optional[str] = None,
    azure_id: Optional[str] = None,
    feature: Optional[str] = None,  # Nuevo filtro
    module: Optional[str] = None,  # Nuevo filtro
    current_user: User = Depends(get_current_active_user)
):
    """Obtener HUs con filtros opcionales y filtrar por proyecto activo"""
    try:
        # Obtener el proyecto activo del usuario
        active_project = db.query(Project).filter(
            Project.user_id == current_user.id,
            Project.is_active == True
        ).first()
        
        if not active_project:
            return {"data": [], "message": "No hay proyecto activo"}
        
        # Construir query base filtrando por proyecto activo
        query = db.query(HU).filter(HU.project_id == active_project.id)
        
        # Aplicar filtros adicionales
        if status:
            # Convertir string a enum para el filtro
            from ..database.models import HUStatus
            try:
                status_enum = HUStatus(status.lower())
                query = query.filter(HU.status == status_enum)
            except ValueError:
                # Si el status no es válido, no filtrar
                pass
        if name:
            query = query.filter(HU.name.ilike(f"%{name}%"))
        if azure_id:
            query = query.filter(HU.azure_id.ilike(f"%{azure_id}%"))
        if feature:
            query = query.filter(HU.feature.ilike(f"%{feature}%"))
        if module:
            query = query.filter(HU.module.ilike(f"%{module}%"))
        
        # Obtener HUs del proyecto activo
        hus = query.order_by(HU.created_at.desc()).all()
        
        # Convertir a formato de respuesta
        result = []
        for hu in hus:
            result.append(hu_to_dict(hu))
        
        return {"data": result, "message": f"Se encontraron {len(result)} HUs del proyecto {active_project.name}"}
        
    except Exception as e:
        print(f"❌ Error obteniendo HUs: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al obtener HUs")

def get_hu_endpoint(hu_id: str, db: Session = Depends(get_db)):
    hu = db.query(HU).filter(HU.id == hu_id).first()
    if not hu:
        raise HTTPException(status_code=404, detail="HU not found")
    return hu_to_dict(hu)

def generate_and_send_tests_endpoint(
    request: TestGenerationRequest, 
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        print(f"🧪 Iniciando generación de tests para HU: {request.azure_id}")
        print(f"   📂 Ruta XRay: {request.xray_path}")
        
        # 🔍 LOGS MEJORADOS: Verificar qué HUs existen en la base de datos
        print(f"🔍 DEBUG: Buscando HU en la base de datos...")
        print(f"   🔍 Azure ID solicitado: '{request.azure_id}'")
        
        # Buscar todas las HUs para ver qué hay disponible
        all_hus = db.query(HU).all()
        print(f"   📊 Total HUs en la base de datos: {len(all_hus)}")
        
        if all_hus:
            print(f"   📋 HUs disponibles:")
            for hu in all_hus[:10]:  # Mostrar solo las primeras 10
                print(f"      - ID: {hu.azure_id} | Nombre: {hu.name[:50]}...")
        else:
            print(f"   ⚠️ La base de datos está vacía!")
        
        # 1. Búsqueda flexible de la HU en la base de datos
        print(f"🔍 Ejecutando búsqueda flexible para azure_id = '{request.azure_id}'...")
        
        # Extraer el número de la HU para búsquedas flexibles
        azure_number = request.azure_id.replace('HU-', '') if 'HU-' in request.azure_id else request.azure_id
        print(f"   🔢 Número extraído: '{azure_number}'")
        
        # Intentar múltiples patrones de búsqueda
        hu = None
        search_patterns = [
            request.azure_id,  # Búsqueda exacta (ej: "HU-129")
            azure_number,      # Solo el número (ej: "129")
            f"HU-{azure_number}",  # Con prefijo (ej: "HU-129")
        ]
        
        print(f"   🔍 Patrones de búsqueda: {search_patterns}")
        
        for pattern in search_patterns:
            print(f"   🔍 Buscando con patrón: '{pattern}'")
            hu = db.query(HU).filter(HU.azure_id == pattern).first()
            if hu:
                print(f"   ✅ HU encontrada con patrón: '{pattern}'")
                break
        
        # 2. Si no se encuentra en la DB, buscar en Azure DevOps
        if not hu:
            print(f"❌ HU no encontrada en la base de datos")
            print(f"🔄 Buscando directamente en Azure DevOps...")
            
            try:
                # Obtener AzureService con credenciales del proyecto activo
                azure_service = get_azure_service_for_user(current_user, db)
                
                # Buscar la HU directamente en Azure DevOps
                print(f"🔍 Fetching HU {azure_number} from Azure DevOps...")
                azure_data = azure_service.fetch_hu(azure_number)
                
                print(f"✅ HU encontrada en Azure DevOps:")
                print(f"   📝 Title: {azure_data['title']}")
                print(f"   🏷️ Feature: {azure_data['feature']}")
                print(f"   📦 Module: {azure_data['module']}")
                
                # Crear un objeto HU temporal con los datos de Azure DevOps
                hu = type('obj', (object,), {
                    'azure_id': azure_number,
                    'name': azure_data['title'],
                    'description': azure_data['description'],
                    'refined_response': azure_data['description'],  # Usar descripción como contenido refinado
                    'markdown_response': azure_data.get('acceptanceCriteria', ''),
                    'feature': azure_data.get('feature'),
                    'module': azure_data.get('module'),
                    'status': 'pending'  # Estado por defecto
                })()
                
                print(f"✅ HU temporal creada con datos de Azure DevOps")
                
            except Exception as azure_error:
                print(f"❌ Error obteniendo HU de Azure DevOps: {str(azure_error)}")
                raise HTTPException(
                    status_code=404, 
                    detail="No se pudo encontrar la HU especificada. Verifica que el ID sea correcto."
                )
        else:
            print(f"✅ HU encontrada en la base de datos:")
            print(f"   📝 ID: {hu.azure_id}")
            print(f"   📝 Nombre: {hu.name}")
            print(f"   📝 Estado: {hu.status}")
            print(f"   📝 Feature: {hu.feature}")
            print(f"   📝 Module: {hu.module}")
        
        # 3. Verificar que tenga contenido para generar tests
        if not hasattr(hu, 'refined_response') or not hu.refined_response:
            print(f"❌ La HU no tiene contenido refinado disponible")
            raise HTTPException(
                status_code=400, 
                detail="La HU no tiene contenido refinado disponible para generar tests."
            )
        
        print(f"✅ HU tiene contenido válido, procediendo con generación de tests...")
        
        # 4. Generar tests con IA
        print(f"🤖 Generando tests with IA...")
        try:
            gemma_service = DeepSeekService()
            test_result = gemma_service.generate_xray_tests(
                hu.refined_response,
                request.xray_path,
                hu.azure_id  # Agregar el parámetro azure_id
            )
            
            print(f"✅ Tests generados exitosamente")
            
            # Extraer los tests clasificados del resultado
            classified_tests = test_result.get('classified_tests', {})
            test_summary = test_result.get('summary', {})
            
            print(f"   📊 Total tests: {test_summary.get('total_tests', 0)}")
            print(f"   🔴 Críticos: {test_summary.get('criticos', 0)}")
            print(f"   🟡 Importantes: {test_summary.get('importantes', 0)}")
            print(f"   🟢 Opcionales: {test_summary.get('opcionales', 0)}")
            
            # Mostrar preview de los tests generados (solo los primeros de cada categoría)
            for category, tests in classified_tests.items():
                if tests and len(tests) > 0:
                    first_test = tests[0]
                    test_name = first_test.get('fields', {}).get('summary', 'Sin nombre')
                    print(f"   📋 {category.capitalize()}: {test_name}")
            
        except Exception as ai_error:
            print(f"❌ Error generando tests con IA: {str(ai_error)}")
            raise HTTPException(
                status_code=500, 
                detail="Error interno al generar tests. Por favor, inténtalo de nuevo."
            )
        
        # 5. Clasificar tests por categoría (ya están clasificados)
        print(f"📂 Tests ya clasificados por categoría...")
        try:
            # Los tests ya vienen clasificados del método generate_xray_tests
            print(f"✅ Tests clasificados exitosamente")
            print(f"   📊 Categorías: {list(classified_tests.keys())}")
            
            for category, tests in classified_tests.items():
                print(f"   📂 {category}: {len(tests)} tests")
                
        except Exception as classify_error:
            print(f"❌ Error procesando tests clasificados: {str(classify_error)}")
            # Continuar sin clasificación
            classified_tests = {"General": []}
        
        # 6. Enviar tests a XRay
        print(f"🚀 Enviando tests a XRay...")
        try:
            print(f"🔐 Obteniendo token de XRay...")
            xray_service = get_xray_service_for_user(current_user, db)
            xray_results = xray_service.send_tests_to_xray_by_category(classified_tests)
            
            print(f"✅ Tests enviados a XRay exitosamente")
            
            # Extraer información del resultado
            total_success = xray_results.get('summary', {}).get('total_success', 0)
            total_failed = xray_results.get('summary', {}).get('total_failed', 0)
            total_tests = xray_results.get('summary', {}).get('total_tests', 0)
            
            print(f"   📊 Tests enviados: {total_success}/{total_tests}")
            print(f"   ❌ Tests fallidos: {total_failed}")
            
            # Mostrar estado por categoría
            for category in ['criticos', 'importantes', 'opcionales']:
                if category in xray_results:
                    category_result = xray_results[category]
                    status = "✅" if category_result.get('success', False) else "❌"
                    count = category_result.get('count', 0)
                    print(f"   {status} {category.capitalize()}: {count} tests")
            
            # Si todos los tests fueron exitosos, usar el resultado completo
            if total_success == total_tests and total_tests > 0:
                print(f"🎉 Todos los tests enviados exitosamente")
            elif total_success > 0:
                print(f"⚠️ Envío parcial: {total_success}/{total_tests} tests enviados")
            else:
                print(f"❌ No se pudo enviar ningún test")
                
        except Exception as xray_error:
            print(f"❌ Error enviando tests a XRay: {str(xray_error)}")
            raise HTTPException(
                status_code=500, 
                detail="Error al enviar tests a XRay. Los tests se generaron correctamente pero no se pudieron enviar."
            )
        
        # 7. Actualizar HU en Azure DevOps (solo si la HU está en la DB y está aprobada)
        if hasattr(hu, 'id') and hasattr(hu, 'status') and hu.status == HUStatus.ACCEPTED:
            print(f"🔄 Actualizando HU en Azure DevOps...")
            try:
                # Actualizar en Azure DevOps con los criterios refinados
                azure_service = get_azure_service_for_user(current_user, db)
                azure_update_success = azure_service.update_hu_in_azure(
                    hu.azure_id, 
                    hu.refined_response, 
                    hu.markdown_response
                )
                
                if azure_update_success:
                    print(f"✅ HU actualizada en Azure DevOps")
                else:
                    print(f"⚠️ No se pudo actualizar HU en Azure DevOps")
                    
            except Exception as azure_error:
                print(f"❌ Error actualizando HU en Azure DevOps: {str(azure_error)}")
                # No fallar el proceso completo por este error
        
        # 8. Retornar resultados
        # Calcular el total de tests generados correctamente
        total_tests_generated = 0
        tests_details = []
        if 'classified_tests' in test_result:
            for category, tests in test_result['classified_tests'].items():
                total_tests_generated += len(tests)
                # Agregar detalles de los tests para mostrar en el frontend
                for test in tests:
                    if isinstance(test, dict):
                        tests_details.append({
                            'summary': test.get('fields', {}).get('summary', 'Sin título'),
                            'description': test.get('fields', {}).get('description', 'Sin descripción'),
                            'testtype': test.get('testtype', 'Manual'),
                            'category': category,
                            'xray_path': test.get('xray_test_repository_folder', ''),
                            'steps_count': len(test.get('steps', []))
                        })
        
        return {
            "success": True,
            "message": f"Tests generados y enviados exitosamente para HU {hu.azure_id}",
            "hu_id": str(hu.id) if hasattr(hu, 'id') else None,
            "azure_id": hu.azure_id,
            "hu_name": hu.name if hasattr(hu, 'name') else f"HU-{hu.azure_id}",
            "tests_generated": total_tests_generated,
            "tests_sent": total_success,
            "xray_path": request.xray_path,
            "tests": tests_details,
            "xray_results": xray_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error general en generación de tests: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def debug_list_hus_endpoint(db: Session = Depends(get_db)):
    """Endpoint de debug para ver todas las HUs en la base de datos"""
    try:
        all_hus = db.query(HU).all()
        
        result = {
            "total_hus": len(all_hus),
            "hus": []
        }
        
        for hu in all_hus:
            result["hus"].append({
                "azure_id": hu.azure_id,
                "name": hu.name,
                "status": hu.status.value,
                "has_refined_response": bool(hu.refined_response and hu.refined_response.strip()),
                "refined_length": len(hu.refined_response) if hu.refined_response else 0,
                "created_at": hu.created_at.isoformat() if hu.created_at else None
            })
        
        return result
        
    except Exception as e:
        return {"error": str(e)}

def debug_find_hu_endpoint(azure_id: str, db: Session = Depends(get_db)):
    """Endpoint de debug para buscar una HU específica"""
    try:
        print(f"🔍 DEBUG: Buscando HU con azure_id = '{azure_id}'")
        
        # Búsqueda exacta
        exact_match = db.query(HU).filter(HU.azure_id == azure_id).first()
        
        # Búsquedas similares
        similar_matches = db.query(HU).filter(HU.azure_id.like(f"%{azure_id}%")).all()
        
        # Buscar por número solamente
        azure_number = azure_id.replace('HU-', '') if 'HU-' in azure_id else azure_id
        number_matches = db.query(HU).filter(
            or_(
                HU.azure_id == azure_number,
                HU.azure_id == f"HU-{azure_number}",
                HU.azure_id.like(f"%{azure_number}%")
            )
        ).all()
        
        result = {
            "search_term": azure_id,
            "exact_match": None,
            "similar_matches": [],
            "number_matches": []
        }
        
        if exact_match:
            result["exact_match"] = {
                "azure_id": exact_match.azure_id,
                "name": exact_match.name,
                "status": exact_match.status.value,
                "has_refined_response": bool(exact_match.refined_response and exact_match.refined_response.strip()),
                "refined_preview": exact_match.refined_response[:200] + "..." if exact_match.refined_response else None
            }
        
        for match in similar_matches:
            result["similar_matches"].append({
                "azure_id": match.azure_id,
                "name": match.name,
                "status": match.status.value
            })
        
        for match in number_matches:
            result["number_matches"].append({
                "azure_id": match.azure_id,
                "name": match.name,
                "status": match.status.value
            })
        
        return result
        
    except Exception as e:
        return {"error": str(e)}

def update_hu_status_endpoint(
    hu_id: str, 
    status_update: HUStatusUpdate, 
    current_user: User,
    db: Session
):
    try:
        print(f"🔄 Updating HU status: {hu_id} -> {status_update.status}")
        
        # Buscar la HU
        hu = db.query(HU).filter(HU.id == hu_id).first()
        if not hu:
            raise HTTPException(status_code=404, detail="HU not found")
        
        print(f"📋 HU found: {hu.azure_id} - {hu.name}")
        print(f"📊 Current status: {hu.status}")
        print(f"📊 New status: {status_update.status}")
        
        if status_update.status == "accepted":
            print(f"✅ ACCEPTING HU: {hu.azure_id} - {hu.name}")
            
            # Verificar que tenga contenido refinado
            if not hu.refined_response or "🤖 Refinando con IA" in hu.refined_response:
                raise HTTPException(
                    status_code=400, 
                    detail="Cannot accept HU that is not refined"
                )
            
            # Parsear contenido refinado para Azure DevOps
            refined_content = hu.refined_response
            markdown_content = hu.markdown_response if hu.markdown_response else refined_content
            
            try:
                print(f"🔄 Updating HU {hu.azure_id} in Azure DevOps...")
                
                # Actualizar en Azure DevOps con los criterios refinados
                azure_service = get_azure_service_for_user(current_user, db)
                azure_update_success = azure_service.update_hu_in_azure(
                    hu.azure_id, 
                    refined_content, 
                    markdown_content
                )
                
                if azure_update_success:
                    print(f"✅ HU {hu.azure_id} successfully updated in Azure DevOps")
                else:
                    print(f"⚠️ HU {hu.azure_id} update to Azure DevOps was not confirmed")
                
            except Exception as azure_error:
                print(f"❌ Failed to update Azure DevOps: {str(azure_error)}")
                print(f"❌ Error type: {type(azure_error).__name__}")
                
                # ✅ OPCIÓN: Decidir si fallar o continuar
                # Uncomment la siguiente línea si quieres que falle cuando Azure DevOps falla:
                # raise HTTPException(status_code=500, detail=f"Failed to update Azure DevOps: {str(azure_error)}")
                
                # Por ahora continuamos con la aprobación local
                azure_update_success = False
            
            # Actualizar estado local
            from datetime import datetime, timezone
            hu.status = HUStatus.ACCEPTED
            hu.updated_at = datetime.now(timezone.utc)
            
            print(f"✅ HU {hu.azure_id} marked as ACCEPTED locally")
            print(f"   🌐 Azure DevOps update: {'✅ Success' if azure_update_success else '❌ Failed'}")
        
        elif status_update.status == "rejected":
            if not status_update.feedback:
                raise HTTPException(status_code=400, detail="Feedback required for rejection")
            
            print(f"❌ REJECTING HU: {hu.azure_id} - {hu.name}")
            print(f"📝 Feedback: {status_update.feedback}")
            
            # Re-refine with feedback
            original_response = hu.refined_response if hu.refined_response else ""
            gemma_service = DeepSeekService()
            refined_text, markdown_text = gemma_service.re_refine_hu(
                status_update.feedback, 
                original_response
            )
            
            # Actualizar con las nuevas versiones
            hu.refined_response = refined_text
            hu.markdown_response = markdown_text
            hu.status = HUStatus.PENDING
            hu.updated_at = datetime.now(timezone.utc)
            
            print(f"🔄 HU {hu.azure_id} re-refined and marked as PENDING")
        
        else:
            raise HTTPException(status_code=400, detail="Status must be 'accepted' or 'rejected'")
        
        db.commit()
        db.refresh(hu)
        
        return hu_to_dict(hu)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR in update_hu_status: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno al actualizar el estado de la HU.")

def delete_hu_endpoint(
    hu_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Eliminar una HU específica"""
    try:
        print(f"🔍 Eliminando HU {hu_id} para usuario {current_user.username}")
        
        # Verificar que la HU existe y pertenece a un proyecto del usuario
        hu = db.query(HU).join(Project).filter(
            HU.id == hu_id,
            Project.user_id == current_user.id
        ).first()
        
        if not hu:
            print(f"❌ HU {hu_id} no encontrada para usuario {current_user.username}")
            raise HTTPException(status_code=404, detail="HU no encontrada")
        
        project_name = hu.project.name if hu.project else "Sin proyecto"
        hu_name = hu.name
        
        print(f"🗑️ Eliminando HU '{hu_name}' del proyecto '{project_name}'")
        
        db.delete(hu)
        db.commit()
        
        print(f"✅ HU '{hu_name}' eliminada exitosamente")
        return {"message": f"HU '{hu_name}' eliminada exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error eliminando HU: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno al eliminar la HU.")

def delete_project_endpoint(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Eliminar un proyecto del usuario"""
    print(f"🔍 DEBUG: delete_project_endpoint llamado con project_id: {project_id}")
    print(f"🔍 DEBUG: Usuario: {current_user.username}")
    
    try:
        print(f"🗑️ Eliminando proyecto {project_id} para usuario {current_user.username}")
        
        # Verificar que el proyecto existe y pertenece al usuario
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == current_user.id
        ).first()
        
        if not project:
            print(f"❌ Proyecto {project_id} no encontrado para usuario {current_user.username}")
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        
        print(f"✅ Proyecto encontrado:")
        print(f"   📝 ID: {project.id}")
        print(f"   📝 Nombre: {project.name}")
        print(f"   📊 Estado activo: {project.is_active}")
        
        # Verificar si es el proyecto activo
        if project.is_active:
            print(f"⚠️ No se puede eliminar el proyecto activo")
            raise HTTPException(
                status_code=400, 
                detail="No se puede eliminar el proyecto activo. Primero establece otro proyecto como activo."
            )
        
        # Verificar si tiene HUs asociadas
        hus_count = db.query(HU).filter(HU.project_id == project_id).count()
        if hus_count > 0:
            print(f"⚠️ El proyecto tiene {hus_count} HUs asociadas")
            raise HTTPException(
                status_code=400, 
                detail=f"No se puede eliminar el proyecto porque tiene {hus_count} HUs asociadas. Elimina las HUs primero."
            )
        
        # Eliminar el proyecto
        db.delete(project)
        db.commit()
        
        print(f"✅ Proyecto {project.name} eliminado exitosamente")
        
        return {"message": f"Proyecto '{project.name}' eliminado exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error eliminando proyecto: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno al eliminar el proyecto.")

def update_project_endpoint(
    project_id: str,
    project_update: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Actualizar un proyecto del usuario"""
    print(f"🔍 DEBUG: update_project_endpoint llamado con project_id: {project_id}")
    print(f"🔍 DEBUG: Usuario: {current_user.username}")
    print(f"🔍 DEBUG: Datos de actualización: {project_update}")
    
    try:
        print(f"✏️ Actualizando proyecto {project_id} para usuario {current_user.username}")
        
        # Verificar que el proyecto existe y pertenece al usuario
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == current_user.id
        ).first()
        
        if not project:
            print(f"❌ Proyecto {project_id} no encontrado para usuario {current_user.username}")
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        
        print(f"✅ Proyecto encontrado:")
        print(f"   📝 ID: {project.id}")
        print(f"   📝 Nombre: {project.name}")
        print(f"   📊 Estado activo: {project.is_active}")
        
        # Preparar datos de actualización
        update_data = {}
        if project_update.name is not None:
            update_data["name"] = project_update.name
        if project_update.description is not None:
            update_data["description"] = project_update.description
        if project_update.azure_devops_token is not None:
            update_data["azure_devops_token"] = project_update.azure_devops_token
        if project_update.azure_org is not None:
            update_data["azure_org"] = project_update.azure_org
        if project_update.azure_project is not None:
            update_data["azure_project"] = project_update.azure_project
        if project_update.client_id is not None:
            update_data["client_id"] = project_update.client_id
        if project_update.client_secret is not None:
            update_data["client_secret"] = project_update.client_secret
        
        print(f"📝 Datos a actualizar: {update_data}")
        
        # Actualizar el proyecto
        for field, value in update_data.items():
            setattr(project, field, value)
        
        db.commit()
        db.refresh(project)
        
        print(f"✅ Proyecto {project.name} actualizado exitosamente")
        
        return ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            is_active=project.is_active,
            azure_org=project.azure_org,
            azure_project=project.azure_project,
            created_at=project.created_at,
            updated_at=project.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error actualizando proyecto: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno al actualizar el proyecto.")

# ==================== RUTAS PARA GESTIÓN DE PROYECTOS ====================

def create_project_endpoint(
    project_data: ProjectCreate, 
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Crear un nuevo proyecto para el usuario autenticado"""
    try:
        print(f"🏗️ Creando proyecto '{project_data.name}' para usuario {current_user.username}")
        print(f"📊 Datos del proyecto:")
        print(f"   📝 Nombre: {project_data.name}")
        print(f"   📝 Descripción: {project_data.description}")
        print(f"   📊 Azure Org: {project_data.azure_org}")
        print(f"   📂 Azure Project: {project_data.azure_project}")
        print(f"   🔑 Token length: {len(project_data.azure_devops_token) if project_data.azure_devops_token else 0}")
        print(f"   🔑 Token preview: {project_data.azure_devops_token[:20] if project_data.azure_devops_token else 'None'}...")
        print(f"   🔑 Client ID: {project_data.client_id}")
        print(f"   🔑 Client Secret length: {len(project_data.client_secret) if project_data.client_secret else 0}")
        
        # Crear nuevo proyecto
        new_project = Project(
            name=project_data.name,
            description=project_data.description,
            user_id=current_user.id,
            azure_devops_token=project_data.azure_devops_token,
            azure_org=project_data.azure_org,
            azure_project=project_data.azure_project,
            client_id=project_data.client_id,
            client_secret=project_data.client_secret,
            is_active=False  # Por defecto inactivo
        )
        
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        
        print(f"✅ Proyecto creado exitosamente:")
        print(f"   📝 ID: {new_project.id}")
        print(f"   📝 Nombre: {new_project.name}")
        print(f"   📊 Azure Org: {new_project.azure_org}")
        print(f"   📂 Azure Project: {new_project.azure_project}")
        print(f"   🔑 Token length: {len(new_project.azure_devops_token) if new_project.azure_devops_token else 0}")
        print(f"   🔑 Token preview: {new_project.azure_devops_token[:20] if new_project.azure_devops_token else 'None'}...")
        
        return ProjectResponse(
            id=new_project.id,
            name=new_project.name,
            description=new_project.description,
            is_active=new_project.is_active,
            azure_org=new_project.azure_org,
            azure_project=new_project.azure_project,
            created_at=new_project.created_at,
            updated_at=new_project.updated_at
        )
        
    except Exception as e:
        print(f"❌ Error creando proyecto: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=400, detail="Error al crear el proyecto. Verifica que todos los campos sean correctos.")

def get_user_projects_endpoint(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtener todos los proyectos del usuario autenticado"""
    try:
        print(f"📋 Obteniendo proyectos para usuario {current_user.username}")
        
        projects = db.query(Project).filter(Project.user_id == current_user.id).all()
        active_project = db.query(Project).filter(
            Project.user_id == current_user.id,
            Project.is_active == True
        ).first()
        
        project_responses = []
        for project in projects:
            project_responses.append(ProjectResponse(
                id=project.id,
                name=project.name,
                description=project.description,
                is_active=project.is_active,
                azure_org=project.azure_org,
                azure_project=project.azure_project,
                created_at=project.created_at,
                updated_at=project.updated_at
            ))
        
        return ProjectListResponse(
            projects=project_responses,
            active_project_id=active_project.id if active_project else None
        )
        
    except Exception as e:
        print(f"❌ Error obteniendo proyectos: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al obtener los proyectos.")

def set_active_project_endpoint(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Establecer un proyecto como activo para el usuario"""
    try:
        print(f"🔄 Estableciendo proyecto {project_id} como activo para usuario {current_user.username}")
        
        # Verificar que el proyecto existe y pertenece al usuario
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == current_user.id
        ).first()
        
        if not project:
            print(f"❌ Proyecto {project_id} no encontrado para usuario {current_user.username}")
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        
        print(f"✅ Proyecto encontrado:")
        print(f"   📝 ID: {project.id}")
        print(f"   📝 Nombre: {project.name}")
        print(f"   📊 Azure Org: {project.azure_org}")
        print(f"   📂 Azure Project: {project.azure_project}")
        print(f"   🔑 Token length: {len(project.azure_devops_token) if project.azure_devops_token else 0}")
        print(f"   🔑 Token preview: {project.azure_devops_token[:20] if project.azure_devops_token else 'None'}...")
        
        # Desactivar todos los proyectos del usuario
        db.query(Project).filter(Project.user_id == current_user.id).update({"is_active": False})
        
        # Activar el proyecto seleccionado
        project.is_active = True
        db.commit()
        db.refresh(project)
        
        print(f"✅ Proyecto {project.name} establecido como activo")
        print(f"   📊 Estado actual: {project.is_active}")
        
        return ProjectResponse(
            id=project.id,
            name=project.name,
            description=project.description,
            is_active=project.is_active,
            azure_org=project.azure_org,
            azure_project=project.azure_project,
            created_at=project.created_at,
            updated_at=project.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error estableciendo proyecto activo: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno al activar el proyecto.")

def get_active_project_endpoint(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtener el proyecto activo del usuario"""
    try:
        print(f"🔍 Obteniendo proyecto activo para usuario {current_user.username}")
        
        active_project = db.query(Project).filter(
            Project.user_id == current_user.id,
            Project.is_active == True
        ).first()
        
        if not active_project:
            print(f"⚠️ No hay proyecto activo para usuario {current_user.username}")
            return None
        
        print(f"✅ Proyecto activo encontrado:")
        print(f"   📝 ID: {active_project.id}")
        print(f"   📝 Nombre: {active_project.name}")
        print(f"   📊 Estado activo: {active_project.is_active}")
        
        return ProjectResponse(
            id=active_project.id,
            name=active_project.name,
            description=active_project.description,
            is_active=active_project.is_active,
            azure_org=active_project.azure_org,
            azure_project=active_project.azure_project,
            created_at=active_project.created_at,
            updated_at=active_project.updated_at
        )
        
    except Exception as e:
        print(f"❌ Error obteniendo proyecto activo: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al obtener el proyecto activo.")

def get_project_hus_endpoint(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtener las HUs asociadas a un proyecto específico"""
    try:
        print(f"🔍 Obteniendo HUs del proyecto {project_id} para usuario {current_user.username}")
        
        # Verificar que el proyecto existe y pertenece al usuario
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == current_user.id
        ).first()
        
        if not project:
            print(f"❌ Proyecto {project_id} no encontrado para usuario {current_user.username}")
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        
        # Obtener todas las HUs del proyecto
        hus = db.query(HU).filter(HU.project_id == project_id).all()
        
        # Convertir a formato de respuesta
        hu_responses = []
        for hu in hus:
            hu_responses.append(hu_to_dict(hu))
        
        return {
            "project": {
                "id": project.id,
                "name": project.name,
                "description": project.description
            },
            "hus": hu_responses,
            "total_count": len(hu_responses)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error obteniendo HUs del proyecto: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al obtener las HUs del proyecto.")

def validate_password_endpoint(
    password: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Validar la contraseña del usuario actual"""
    try:
        print(f"🔐 Validando contraseña para usuario {current_user.username}")
        
        # Verificar la contraseña usando la función de verificación existente
        if not verify_password(password, current_user.hashed_password):
            print(f"❌ Contraseña incorrecta para usuario {current_user.username}")
            # Usar un código de error específico para contraseña incorrecta
            raise HTTPException(status_code=422, detail="Contraseña incorrecta")
        
        print(f"✅ Contraseña válida para usuario {current_user.username}")
        return {"message": "Contraseña válida", "valid": True}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error validando contraseña: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al validar la contraseña.")
