from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from datetime import datetime, timezone

from ..database.connection import get_db
from ..database.models import HU, HUStatus
from ..schemas.hu_schemas import HUCreate, HUStatusUpdate, HUResponse, TestGenerationRequest
from ..services.azure_service import AzureService
from ..services.deepseek_service import DeepSeekService
from ..services.xray_service import XRayService

# Initialize services
azure_service = AzureService()
gemma_service = DeepSeekService()  # Mantenemos el nombre de la variable
xray_service = XRayService()

# Helper function
def hu_to_dict(hu: HU) -> dict:
    return {
        "id": str(hu.id),
        "azure_id": hu.azure_id,
        "name": hu.name,
        "description": hu.description,
        "status": hu.status.value,
        "refined_response": hu.refined_response,  # Ahora es texto plano
        "markdown_response": hu.markdown_response,  # Ahora es texto plano
        "feature": hu.feature,  # Nuevo campo
        "module": hu.module,  # Nuevo campo
        "created_at": hu.created_at.isoformat() if hu.created_at else None,
        "updated_at": hu.updated_at.isoformat() if hu.updated_at else None
    }

def create_hu_endpoint(hu_data: HUCreate, db: Session = Depends(get_db)):
    try:
        # Check if exists
        existing = db.query(HU).filter(HU.azure_id == hu_data.azure_id).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"HU {hu_data.azure_id} already exists")
        
        # ✅ MEJORADO: Fetch con información más completa
        print(f"🔍 Fetching HU {hu_data.azure_id} from Azure DevOps...")
        azure_data = azure_service.fetch_hu(hu_data.azure_id)
        print(f"✅ Azure DevOps data retrieved:")
        print(f"   📝 Title: {azure_data['title']}")
        print(f"   🏷️ Feature: {azure_data['feature']}")
        print(f"   📦 Module: {azure_data['module']}")
        
        # Create HU immediately with basic data
        new_hu = HU(
            azure_id=hu_data.azure_id,
            name=azure_data['title'],
            description=azure_data['description'],
            refined_response="🤖 Refinando con IA... Por favor espera.",
            markdown_response="🤖 Refinando con IA... Por favor espera.",
            feature=azure_data.get('feature'),
            module=azure_data.get('module')
        )
        
        db.add(new_hu)
        db.commit()
        db.refresh(new_hu)
        print(f"✅ HU created in database with ID: {new_hu.id}")
        
        # ✅ MEJORADO: Refinamiento con información adicional
        print(f"🤖 Starting enhanced AI refinement...")
        try:
            refined_text, markdown_text = gemma_service.refine_hu(
                azure_data.get('title', ''), 
                azure_data.get('description', ''), 
                azure_data.get('acceptanceCriteria', ''),
                azure_data.get('feature', ''),
                azure_data.get('module', '')
            )
            
            # Update with refined content
            new_hu.refined_response = refined_text
            new_hu.markdown_response = markdown_text
            db.commit()
            db.refresh(new_hu)
            print(f"✅ Enhanced AI refinement completed")
            
        except Exception as ai_error:
            print(f"❌ AI refinement failed: {str(ai_error)}")
            new_hu.refined_response = f"❌ Error refinando: {str(ai_error)}"
            new_hu.markdown_response = f"❌ Error refinando: {str(ai_error)}"
            db.commit()
            db.refresh(new_hu)
        
        return hu_to_dict(new_hu)
    
    except Exception as e:
        print(f"❌ Error creating HU: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

def get_hus_endpoint(
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    name: Optional[str] = None,
    azure_id: Optional[str] = None,
    feature: Optional[str] = None,  # Nuevo filtro
    module: Optional[str] = None  # Nuevo filtro
):
    query = db.query(HU)
    
    if status:
        query = query.filter(HU.status == HUStatus(status))
    if name:
        query = query.filter(HU.name.ilike(f"%{name}%"))
    if azure_id:
        query = query.filter(HU.azure_id == azure_id)
    if feature:
        query = query.filter(HU.feature.ilike(f"%{feature}%"))
    if module:
        query = query.filter(HU.module.ilike(f"%{module}%"))
    
    hus = query.order_by(HU.created_at.desc()).all()
    return [hu_to_dict(hu) for hu in hus]

def get_hu_endpoint(hu_id: str, db: Session = Depends(get_db)):
    hu = db.query(HU).filter(HU.id == hu_id).first()
    if not hu:
        raise HTTPException(status_code=404, detail="HU not found")
    return hu_to_dict(hu)

def generate_and_send_tests_endpoint(request: TestGenerationRequest, db: Session = Depends(get_db)):
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
        
        if not hu:
            print(f"❌ HU no encontrada con ningún patrón")
            
            # Buscar HUs similares para debug
            print(f"🔍 Buscando HUs similares...")
            similar_hus = db.query(HU).filter(
                or_(
                    HU.azure_id.like(f"%{azure_number}%"),
                    HU.azure_id.like(f"%{request.azure_id}%")
                )
            ).all()
            
            if similar_hus:
                print(f"   📋 HUs similares encontradas:")
                for similar in similar_hus:
                    print(f"      - ID: '{similar.azure_id}' | Nombre: {similar.name}")
            else:
                print(f"   ❌ No se encontraron HUs similares")
            
            raise HTTPException(
                status_code=404, 
                detail=f"HU {request.azure_id} no encontrada. Patrones probados: {search_patterns}. Total HUs disponibles: {len(all_hus)}"
            )
        
        print(f"✅ HU encontrada exitosamente:")
        print(f"   📝 ID: {hu.azure_id}")
        print(f"   📝 Nombre: {hu.name}")
        print(f"   📊 Estado: {hu.status.value}")
        print(f"   🏷️ Feature: {hu.feature}")
        print(f"   📦 Módulo: {hu.module}")
        
        # 2. Verificar que tenga contenido refinado
        print(f"🔍 Verificando contenido refinado...")
        
        if not hu.refined_response:
            print(f"❌ refined_response es None")
            raise HTTPException(status_code=400, detail="La HU no tiene contenido refinado disponible (campo vacío)")
        
        refined_content = hu.refined_response.strip()
        if not refined_content:
            print(f"❌ refined_response está vacío después de strip()")
            raise HTTPException(status_code=400, detail="La HU no tiene contenido refinado disponible (contenido vacío)")
        
        if "🤖 Refinando con IA" in refined_content:
            print(f"⚠️ La HU aún se está refinando")
            raise HTTPException(status_code=400, detail="La HU aún se está procesando. Por favor espera unos momentos.")
        
        if "❌ Error refinando" in refined_content:
            print(f"❌ La HU tiene errores en el refinamiento")
            raise HTTPException(status_code=400, detail="La HU tuvo errores durante el refinamiento. Por favor refínala nuevamente.")
        
        print(f"✅ Contenido refinado válido:")
        print(f"   📏 Longitud: {len(refined_content)} caracteres")
        print(f"   📄 Vista previa: {refined_content[:200]}...")
        
        # 3. Generar tests clasificados con IA
        print(f"🤖 Generando casos de test clasificados con IA...")
        print(f"   🤖 Servicio: DeepSeekService (Gemma)")
        print(f"   📊 Input: {len(refined_content)} chars de contenido refinado")
        
        try:
            test_result = gemma_service.generate_xray_tests(
                refined_content,
                request.xray_path, 
                request.azure_id
            )
            
            classified_tests = test_result['classified_tests']
            test_summary = test_result['summary']
            
            print(f"✅ IA generó {test_summary['total_tests']} casos de test clasificados:")
            print(f"   🔴 Críticos: {test_summary['criticos']}")
            print(f"   🟡 Importantes: {test_summary['importantes']}")
            print(f"   🟢 Opcionales: {test_summary['opcionales']}")
            
        except Exception as ai_error:
            print(f"❌ Error en generación de IA: {str(ai_error)}")
            print(f"❌ Tipo de error: {type(ai_error).__name__}")
            raise HTTPException(status_code=500, detail=f"Error generando tests con IA: {str(ai_error)}")
        
        # 4. Guardar tests clasificados en la HU
        print(f"💾 Guardando tests clasificados en la base de datos...")
        try:
            hu.tests_generated = {
                "classified_tests": classified_tests,
                "summary": test_summary,
                "xray_path": request.xray_path,
                "generated_at": datetime.now().isoformat()
            }
            
            db.commit()
            db.refresh(hu)
            print(f"✅ Tests clasificados guardados en la base de datos")
            
        except Exception as db_error:
            print(f"❌ Error guardando en la base de datos: {str(db_error)}")
            # Continuamos sin fallar, ya que los tests se generaron correctamente
        
        # 5. Enviar tests clasificados a XRay por categorías
        print(f"📤 Enviando tests clasificados a XRay por categorías...")
        xray_results = {"summary": {"total_success": 0, "total_failed": 0}}
        
        try:
            print(f"🔐 Obteniendo token de XRay...")
            xray_results = xray_service.send_tests_to_xray_by_category(classified_tests)
            
            success_count = xray_results["summary"]["total_success"]
            failed_count = xray_results["summary"]["total_failed"] 
            total_count = xray_results["summary"]["total_tests"]
            
            if success_count == total_count:
                result_message = f"✅ {total_count} casos de test generados y enviados exitosamente a XRay (🔴{test_summary['criticos']} 🟡{test_summary['importantes']} 🟢{test_summary['opcionales']})"
            elif success_count > 0:
                result_message = f"⚠️ {success_count}/{total_count} tests enviados exitosamente a XRay. {failed_count} fallaron."
            else:
                result_message = f"❌ {total_count} tests generados pero falló el envío a XRay"
                
        except Exception as xray_error:
            print(f"❌ Error enviando a XRay: {str(xray_error)}")
            print(f"❌ Tipo de error XRay: {type(xray_error).__name__}")
            result_message = f"✅ {test_summary['total_tests']} casos de test generados y clasificados, pero falló el envío a XRay: {str(xray_error)}"
            xray_results = {"summary": {"total_success": 0, "total_failed": test_summary['total_tests']}}
        
        # 6. Preparar respuesta detallada
        response_data = {
            "success": True,
            "message": result_message,
            "hu_id": hu.azure_id,
            "hu_name": hu.name,
            "tests_generated": test_summary['total_tests'],
            "tests_by_category": {
                "criticos": test_summary['criticos'],
                "importantes": test_summary['importantes'],
                "opcionales": test_summary['opcionales']
            },
            "xray_path": request.xray_path,
            "xray_results": xray_results,
            "classified_tests": classified_tests
        }
        
        print(f"✅ Proceso completado exitosamente")
        print(f"   📊 Tests clasificados: 🔴{test_summary['criticos']} 🟡{test_summary['importantes']} 🟢{test_summary['opcionales']}")
        print(f"   📤 XRay: {xray_results['summary']['total_success']}/{test_summary['total_tests']} enviados exitosamente")
        
        return response_data
        
    except HTTPException as http_exc:
        print(f"❌ HTTP Exception: {http_exc.status_code} - {http_exc.detail}")
        raise
        
    except Exception as e:
        print(f"❌ Error inesperado en generate_and_send_tests:")
        print(f"   ❌ Tipo: {type(e).__name__}")
        print(f"   ❌ Mensaje: {str(e)}")
        print(f"   ❌ Request data: xray_path={request.xray_path}, azure_id={request.azure_id}")
        
        # Información adicional de debug
        try:
            total_hus = db.query(HU).count()
            print(f"   🔍 Total HUs in DB: {total_hus}")
        except:
            print(f"   ❌ No se pudo consultar la base de datos")
        
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

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

def update_hu_status_endpoint(hu_id: str, status_update: HUStatusUpdate, db: Session = Depends(get_db)):
    try:
        hu = db.query(HU).filter(HU.id == hu_id).first()
        if not hu:
            raise HTTPException(status_code=404, detail="HU not found")
        
        if status_update.status == "accepted":
            print(f"🎯 APPROVING HU: {hu.azure_id} - {hu.name}")
            
            # ✅ VERIFICAR que tenemos contenido para enviar
            if not hu.refined_response or hu.refined_response.strip() == "":
                print(f"⚠️ WARNING: No refined response to send to Azure DevOps")
                refined_content = f"HU aprobada por QA sin contenido refinado. Título: {hu.name}"
            else:
                refined_content = hu.refined_response
                print(f"📄 Will send {len(refined_content)} characters to Azure DevOps")
            
            if not hu.markdown_response or hu.markdown_response.strip() == "":
                print(f"⚠️ WARNING: No markdown response to send to Azure DevOps")
                markdown_content = refined_content  # Usar el mismo contenido
            else:
                markdown_content = hu.markdown_response
                print(f"📋 Will send {len(markdown_content)} characters as acceptance criteria")
            
            # 🆕 NUEVA FUNCIONALIDAD: Actualizar en Azure DevOps cuando se aprueba
            azure_update_success = False
            try:
                print(f"🔄 Updating HU {hu.azure_id} in Azure DevOps...")
                
                # Actualizar en Azure DevOps con los criterios refinados
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
        raise HTTPException(status_code=500, detail=str(e))
