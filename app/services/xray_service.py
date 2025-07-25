import os
import requests
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

class XRayService:
    def __init__(self):
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.auth_url = os.getenv("AUTH_URL")
        self.import_url = os.getenv("XRAY_IMPORT_URL")
        
    def get_auth_token(self):
        """Obtener token de autenticación de XRay"""
        try:
            response = requests.post(
                self.auth_url,
                json={"client_id": self.client_id, "client_secret": self.client_secret},
                timeout=30,
            )
            response.raise_for_status()
            
            try:
                data = response.json()
            except ValueError:
                raise Exception("Error: respuesta de autenticación no es JSON válido")
            
            token = None
            if isinstance(data, dict):
                token = data.get("access_token") or data.get("token") or data.get("jwt")
            elif isinstance(data, str):
                token = data
            
            if not token:
                raise Exception("Error: respuesta de autenticación sin token")
            
            print(f"✅ Token obtenido: {token[:10]}...")
            return token
            
        except requests.RequestException as exc:
            raise Exception(f"Error obteniendo token: {exc}")
    
    def send_tests_to_xray(self, tests_data: List[dict]) -> bool:
        """Enviar tests generados a XRay"""
        token = self.get_auth_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        print(f"📤 Enviando {len(tests_data)} tests a XRay...")
        try:
            response = requests.post(self.import_url, json=tests_data, headers=headers, timeout=30)
            response.raise_for_status()
            
            print(f"✅ Tests enviados exitosamente a XRay")
            if response.text:
                print(f"📄 Respuesta de XRay: {response.text}")
            
            return True
            
        except requests.HTTPError:
            error_text = response.text if hasattr(response, "text") else ""
            print(f"❌ Error HTTP al enviar a XRay: {response.status_code} {error_text}")
            raise Exception(f"Error HTTP al enviar a XRay: {response.status_code}")
            
        except requests.RequestException as exc:
            print(f"❌ Error de conexión al enviar a XRay: {exc}")
            raise Exception(f"Error de conexión al enviar a XRay: {exc}")

    def send_tests_to_xray_by_category(self, classified_tests: dict) -> dict:
        """Enviar tests clasificados a XRay por categorías de forma SECUENCIAL"""
        token = self.get_auth_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        results = {
            "criticos": {"success": False, "message": "", "count": 0},
            "importantes": {"success": False, "message": "", "count": 0},
            "opcionales": {"success": False, "message": "", "count": 0},
            "summary": {"total_success": 0, "total_failed": 0, "total_tests": 0}
        }
        
        categories = ['criticos', 'importantes', 'opcionales']
        category_labels = {'criticos': '🔴 Críticos', 'importantes': '🟡 Importantes', 'opcionales': '🟢 Opcionales'}
        
        for category_index, category in enumerate(categories):
            if category not in classified_tests or not classified_tests[category]:
                print(f"⚠️ Categoría {category} vacía, omitiendo...")
                continue
                
            tests_data = classified_tests[category]
            test_count = len(tests_data)
            category_label = category_labels[category]
            
            print(f"📤 Enviando {test_count} tests de categoría {category_label} a XRay...")
            
            # ✅ ESPERAR ENTRE ENVÍOS para evitar jobs concurrentes
            if category_index > 0:  # No esperar en el primer envío
                wait_time = 10 + (category_index * 5)  # 10s, 15s progresivo
                print(f"   ⏳ Esperando {wait_time}s para evitar jobs concurrentes...")
                import time
                time.sleep(wait_time)
            
            # ✅ REINTENTOS ESPECÍFICOS PARA XRAY
            max_attempts = 3
            success = False
            
            for attempt in range(1, max_attempts + 1):
                try:
                    print(f"   🔄 Intento {attempt}/{max_attempts} para {category_label}...")
                    
                    response = requests.post(self.import_url, json=tests_data, headers=headers, timeout=45)
                    
                    if response.status_code == 200:
                        print(f"✅ {category_label}: {test_count} tests enviados exitosamente")
                        if response.text:
                            response_data = response.json() if response.text else {}
                            job_id = response_data.get('jobId', 'N/A')
                            print(f"📄 Job ID ({category}): {job_id}")
                        
                        results[category] = {
                            "success": True,
                            "message": f"{test_count} tests enviados exitosamente",
                            "count": test_count
                        }
                        results["summary"]["total_success"] += test_count
                        success = True
                        break
                        
                    elif response.status_code == 400:
                        error_data = response.json() if response.text else {}
                        error_msg = error_data.get('error', response.text)
                        
                        if "job to import tests is already in progress" in error_msg.lower():
                            # Job en progreso - esperar más tiempo
                            if attempt < max_attempts:
                                wait_time = 15 + (attempt * 10)  # 25s, 35s, 45s
                                print(f"❌ {category_label}: Job en progreso. Esperando {wait_time}s más...")
                                import time
                                time.sleep(wait_time)
                                continue
                            else:
                                print(f"❌ {category_label}: Job persistente después de {max_attempts} intentos")
                                error_final = f"Job en progreso persistente: {error_msg}"
                        else:
                            # Otro error 400
                            print(f"❌ {category_label}: Error 400 - {error_msg}")
                            error_final = f"Error 400: {error_msg}"
                            break  # No reintentar otros errores 400
                    
                    else:
                        # Otros códigos de error HTTP
                        error_text = response.text if hasattr(response, "text") else ""
                        error_msg = f"Error HTTP {response.status_code}: {error_text}"
                        
                        if attempt < max_attempts:
                            print(f"❌ {category_label}: {error_msg}. Reintentando...")
                            import time
                            time.sleep(5 + attempt * 3)  # 8s, 11s, 14s
                            continue
                        else:
                            error_final = error_msg
                
                except requests.RequestException as exc:
                    error_msg = f"Error de conexión: {exc}"
                    
                    if attempt < max_attempts:
                        print(f"❌ {category_label}: {error_msg}. Reintentando...")
                        import time
                        time.sleep(5 + attempt * 3)
                        continue
                    else:
                        error_final = error_msg
                
                except Exception as exc:
                    error_final = f"Error inesperado: {exc}"
                    break
            
            # Si no tuvo éxito después de todos los intentos
            if not success:
                print(f"❌ {category_label}: Falló después de {max_attempts} intentos - {error_final}")
                results[category] = {
                    "success": False,
                    "message": error_final,
                    "count": test_count
                }
                results["summary"]["total_failed"] += test_count
            
            results["summary"]["total_tests"] += test_count
        
        # Resumen final
        total_success = results["summary"]["total_success"]
        total_failed = results["summary"]["total_failed"]
        total_tests = results["summary"]["total_tests"]
        
        print(f"\n📊 RESUMEN FINAL DE ENVÍO A XRAY:")
        print(f"   ✅ Exitosos: {total_success}/{total_tests}")
        print(f"   ❌ Fallidos: {total_failed}/{total_tests}")
        print(f"   🔴 Críticos: {results['criticos']['count']} ({'✅' if results['criticos']['success'] else '❌'})")
        print(f"   🟡 Importantes: {results['importantes']['count']} ({'✅' if results['importantes']['success'] else '❌'})")
        print(f"   🟢 Opcionales: {results['opcionales']['count']} ({'✅' if results['opcionales']['success'] else '❌'})")
        
        # ✅ INFORMACIÓN ADICIONAL DE ÉXITO
        if total_success == total_tests:
            print(f"🎉 ¡PERFECTO! Todos los tests fueron enviados exitosamente a XRay")
        elif total_success > 0:
            print(f"⚠️ Envío parcial: {total_success}/{total_tests} tests enviados")
        else:
            print(f"❌ No se pudo enviar ningún test a XRay")
        
        return results