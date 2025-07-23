import os
import re
import json
import requests
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

class AzureService:
    def __init__(self):
        self.token = os.getenv("AZURE_DEVOPS_TOKEN")
        self.org = os.getenv("AZURE_ORG", "blackbird-labs-org")
        self.project = os.getenv("AZURE_PROJECT", "DeUna Dropshipping")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def parse_refined_content(self, refined_content: str) -> dict:
        """
        Parser que usa IA para analizar directamente el contenido refinado de la DB
        y generar HTML formateado para Azure DevOps
        """
        if not refined_content:
            return {
                'description': "<p>Historia de usuario sin contenido refinado</p>",
                'acceptance_criteria': "<p>Sin criterios de aceptación definidos</p>"
            }
        
        print(f"🤖 Analizando contenido con IA directa para HTML ({len(refined_content)} chars)...")
        
        # Usar IA para analizar y separar en formato HTML
        ai_result = self._analyze_with_ai_html(refined_content)
        
        if ai_result:
            print("✅ IA analysis HTML exitoso")
            return ai_result
        else:
            print("❌ IA falló, usando fallback HTML")
            return self._simple_fallback_html(refined_content)

    def _analyze_with_ai_html(self, content: str) -> dict:
        """
        Usar IA para analizar y separar el contenido en descripción y criterios 
        GENERANDO HTML FORMATEADO para Azure DevOps
        """
        try:
            # Importar DeepSeekService dinámicamente para evitar imports circulares
            from .deepseek_service import DeepSeekService
            gemma_service = DeepSeekService()
            
            # Prompt ESPECÍFICO para generar HTML formateado
            prompt = f"""Analiza este contenido de historia de usuario y conviértelo al formato HTML específico que requiere Azure DevOps:

    CONTENIDO PARA ANALIZAR:
    {content}

    FORMATO REQUERIDO (HTML VÁLIDO PARA AZURE DEVOPS):

    La DESCRIPCIÓN debe tener esta estructura HTML exacta:
    - Párrafo principal con la funcionalidad
    - Lista con el rol del usuario y flujo
    - Usar <p>, <strong>, <ol>, <li>

    Los CRITERIOS deben tener esta estructura HTML exacta:
    - Títulos con <h3> para cada sección (1. Intención Macro, 2. Flujo Funcional, etc.)
    - Párrafos <p> con escenarios
    - <strong> para Given/When/Then/Y
    - <br> para saltos de línea dentro del mismo párrafo

    EJEMPLO DEL FORMATO HTML EXACTO QUE QUIERO:

    DESCRIPCIÓN HTML:
    <p><strong>Funcionalidad:</strong> Permite al usuario registrarse e iniciar sesión usando su cuenta de Google para simplificar el acceso.</p>
    <p><strong>Rol del usuario:</strong> Usuario nuevo o existente</p>
    <p><strong>Flujo de usuario:</strong></p>
    <ol>
    <li>El usuario navega a la página de registro/inicio de sesión.</li>
    <li>Hace clic en el botón "Iniciar Sesión con Google".</li>
    <li>Es redirigido a Google para autenticar.</li>
    <li>Completa el proceso y regresa a la plataforma.</li>
    </ol>

    CRITERIOS HTML:
    <h3>1. Intención Macro (Propuesta de Valor)</h3>
    <p><strong>Escenario:</strong> Registrarse exitosamente con Google<br>
    <strong>Dado</strong> que el usuario hace clic en "Iniciar Sesión con Google"<br>
    <strong>Cuando</strong> completa la autenticación en Google<br>
    <strong>Entonces</strong> debe ser redirigido al dashboard de la plataforma<br>
    <strong>Y</strong> su cuenta debe crearse automáticamente con los datos de Google.<br>
    <strong>ModoVerificación:</strong> Manual</p>

    <h3>2. Flujo Funcional Completo</h3>
    <p><strong>Escenario:</strong> Proceso completo de autenticación<br>
    <strong>Dado</strong> que el usuario selecciona autenticación con Google<br>
    <strong>Cuando</strong> autoriza el acceso a sus datos<br>
    <strong>Entonces</strong> el sistema debe validar la información<br>
    <strong>Y</strong> crear o actualizar la cuenta del usuario.<br>
    <strong>ModoVerificación:</strong> Manual</p>

    <h3>3. Interacción de Componentes UI</h3>
    <p><strong>Escenario:</strong> Botón de Google visible y funcional<br>
    <strong>Dado</strong> que el usuario está en la página de login<br>
    <strong>Cuando</strong> ve el botón "Iniciar Sesión con Google"<br>
    <strong>Entonces</strong> debe estar claramente visible y ser clickeable<br>
    <strong>Y</strong> redirigir correctamente a Google.<br>
    <strong>ModoVerificación:</strong> Manual</p>

    <h3>4. Validación de Datos y Reglas</h3>
    <p><strong>Escenario:</strong> Validar datos recibidos de Google<br>
    <strong>Dado</strong> que Google proporciona los datos del usuario<br>
    <strong>Cuando</strong> el sistema los recibe<br>
    <strong>Entonces</strong> debe validar el email como único<br>
    <strong>Y</strong> almacenar correctamente la información.<br>
    <strong>ModoVerificación:</strong> Automático</p>

    <h3>5. Casos de Borde y Errores</h3>
    <p><strong>Escenario:</strong> Error de conexión con Google<br>
    <strong>Dado</strong> que ocurre un problema con el servicio de Google<br>
    <strong>Cuando</strong> el usuario intenta autenticarse<br>
    <strong>Entonces</strong> debe mostrar un mensaje de error claro<br>
    <strong>Y</strong> permitir al usuario intentar nuevamente.<br>
    <strong>ModoVerificación:</strong> Manual</p>

    RESPONDE SOLO ESTE JSON (con HTML válido dentro):
    {{
        "description": "[HTML de descripción con <p>, <strong>, <ol>, <li>]",
        "acceptance_criteria": "[HTML de criterios con <h3>, <p>, <strong>, <br>]"
    }}

    REGLAS CRÍTICAS PARA HTML:
    - USA HTML válido: <p>, <strong>, <h3>, <ol>, <li>, <br>
    - Los <h3> son para títulos de secciones (1. Intención Macro, etc.)
    - Los <strong> son para Given/When/Then/Y/Escenario/ModoVerificación
    - Los <br> son para saltos de línea dentro del mismo párrafo
    - Los <p> contienen cada escenario completo
    - RESPONDE SOLO JSON VÁLIDO con HTML dentro
    """
            payload = {
                "model": "mistralai/mistral-small-3.2-24b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 3500,
                "temperature": 0.1  # Muy baja para ser consistente
            }

            print("📡 Enviando a IA para generar HTML...")
            response = requests.post(
                gemma_service.base_url,
                headers=gemma_service.headers,
                json=payload,
                timeout=50
            )

            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content'].strip()
                
                print(f"📝 IA response HTML: {len(ai_response)} chars")
                
                # Limpiar respuesta
                clean_response = ai_response.replace('```json', '').replace('```', '').strip()
                
                # Intentar parsear JSON
                try:
                    parsed_data = json.loads(clean_response)
                    
                    if 'description' in parsed_data and 'acceptance_criteria' in parsed_data:
                        desc_html = parsed_data['description'].strip()
                        crit_html = parsed_data['acceptance_criteria'].strip()
                        
                        # Validar que contenga HTML
                        if ('<p>' in desc_html or '<strong>' in desc_html) and ('<h3>' in crit_html or '<p>' in crit_html):
                            print(f"✅ IA HTML parsing exitoso - Desc: {len(desc_html)}, Crit: {len(crit_html)}")
                            
                            # Mostrar preview del HTML generado
                            print(f"🎨 HTML Description preview:")
                            print(f"{desc_html[:300]}...")
                            print(f"🎨 HTML Criteria preview:")
                            print(f"{crit_html[:300]}...")
                            
                            return {
                                'description': desc_html,
                                'acceptance_criteria': crit_html
                            }
                        else:
                            print("⚠️ IA no generó HTML válido")
                    
                except json.JSONDecodeError as e:
                    print(f"❌ JSON parse error: {e}")
                    print(f"Response: {clean_response[:300]}")
            
            else:
                print(f"❌ IA API error: {response.status_code}")
        
        except Exception as e:
            print(f"❌ Error en IA HTML: {e}")
        
        return None

    def _simple_fallback_html(self, content: str) -> dict:
        """
        Fallback que genera HTML básico cuando la IA falla
        MEJORADO para manejar contenido malformado con markdown mezclado
        """
        print("🔄 Fallback HTML mejorado...")
        
        # PASO 1: Limpiar y normalizar el contenido
        content = self._clean_and_normalize_content(content)
        
        lines = content.split('\n')
        
        # PASO 2: Encontrar división inteligente entre descripción y criterios
        split_point = self._find_smart_split_point(lines)
        
        # PASO 3: Dividir contenido
        if split_point > 3:
            desc_lines = lines[:split_point]
            crit_lines = lines[split_point:]
        else:
            # División por contenido si no encontramos split point claro
            mid = len(lines) // 2
            desc_lines = lines[:mid]
            crit_lines = lines[mid:]
        
        print(f"📊 División inteligente: {len(desc_lines)} líneas para descripción, {len(crit_lines)} líneas para criterios")
        
        # PASO 4: Generar descripción en HTML
        description_html = self._generate_description_html(desc_lines)
        
        # PASO 5: Generar criterios en HTML
        criteria_html = self._generate_criteria_html(crit_lines)
        
        print(f"✅ Fallback HTML mejorado generado:")
        print(f"   📝 Description HTML: {len(description_html)} chars")
        print(f"   ✅ Criteria HTML: {len(criteria_html)} chars")
        
        return {
            'description': description_html,
            'acceptance_criteria': criteria_html
        }

    def _clean_and_normalize_content(self, content: str) -> str:
        """
        Limpia y normaliza contenido malformado con markdown mezclado
        """
        print("🧹 Limpiando contenido malformado...")
        
        # Remover múltiples espacios y líneas vacías
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r' +', ' ', content)
        
        # Normalizar títulos de markdown inconsistentes
        content = re.sub(r'^###+\s*', '### ', content, flags=re.MULTILINE)
        content = re.sub(r'^##\s*', '## ', content, flags=re.MULTILINE)
        
        # Limpiar asteriscos sueltos o malformados
        content = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', content)
        
        # Normalizar bullets points
        content = re.sub(r'^[\*\-]\s+', '• ', content, flags=re.MULTILINE)
        
        print(f"✅ Contenido normalizado: {len(content)} chars")
        return content

    def _find_smart_split_point(self, lines: list) -> int:
        """
        Encuentra el punto de división inteligente entre descripción y criterios
        """
        print("🔍 Buscando punto de división inteligente...")
        
        # Indicadores fuertes de criterios
        strong_indicators = [
            'criterios de aceptación',
            'criterios detallados', 
            'escenario:',
            'dado que',
            'cuando el',
            'entonces el',
            '1. intención macro',
            '### 1.',
            'flujo funcional'
        ]
        
        # Indicadores débiles de criterios
        weak_indicators = [
            'validación',
            'verificación',
            'error',
            'casos',
            'prueba'
        ]
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Buscar indicadores fuertes
            for indicator in strong_indicators:
                if indicator in line_lower:
                    print(f"✅ Indicador fuerte encontrado en línea {i}: '{indicator}' en '{line[:50]}...'")
                    return i
            
            # Si llegamos a la mitad sin indicadores fuertes, buscar débiles
            if i > len(lines) // 3:
                for indicator in weak_indicators:
                    if indicator in line_lower and len(line.strip()) > 10:
                        print(f"✅ Indicador débil encontrado en línea {i}: '{indicator}' en '{line[:50]}...'")
                        return i
        
        # Si no encontramos nada, dividir en 60% descripción, 40% criterios
        split_at = int(len(lines) * 0.6)
        print(f"⚠️ No se encontraron indicadores claros. División por defecto en línea {split_at}")
        return split_at

    def _generate_description_html(self, desc_lines: list) -> str:
        """
        Genera HTML para la descripción
        """
        print("📝 Generando descripción HTML...")
        
        # Combinar líneas y limpiar
        desc_text = '\n'.join(desc_lines).strip()
        
        # Extraer información clave
        functionality_text = self._extract_functionality(desc_text)
        user_role = self._extract_user_role(desc_text)
        user_flow = self._extract_user_flow(desc_text)
        
        # Construir HTML
        html_parts = []
        
        # Funcionalidad principal
        if functionality_text:
            html_parts.append(f"<p><strong>Funcionalidad:</strong> {functionality_text}</p>")
        else:
            # Buscar el primer párrafo significativo
            first_meaningful = self._find_first_meaningful_paragraph(desc_text)
            if first_meaningful:
                html_parts.append(f"<p><strong>Funcionalidad:</strong> {first_meaningful}</p>")
        
        # Rol del usuario
        if user_role:
            html_parts.append(f"<p><strong>Rol del usuario:</strong> {user_role}</p>")
        
        # Flujo de usuario
        if user_flow:
            html_parts.append("<p><strong>Flujo de usuario:</strong></p>")
            html_parts.append("<ol>")
            for step in user_flow[:8]:  # Máximo 8 pasos
                html_parts.append(f"<li>{step}</li>")
            html_parts.append("</ol>")
        
        # Si no hay contenido, usar fallback
        if not html_parts:
            return "<p><strong>Funcionalidad:</strong> Registro e inicio de sesión con Google para simplificar el acceso de usuarios.</p>"
        
        return ''.join(html_parts)

    def _generate_criteria_html(self, crit_lines: list) -> str:
        """
        Genera HTML para los criterios de aceptación
        """
        print("✅ Generando criterios HTML...")
        
        # Agrupar líneas en secciones
        sections = self._group_criteria_sections(crit_lines)
        
        if not sections:
            print("⚠️ No se encontraron secciones de criterios, usando plantilla")
            return self._generate_default_criteria_html()
        
        # Títulos predefinidos para las 5 secciones
        section_titles = [
            "1. Intención Macro (Propuesta de Valor)",
            "2. Flujo Funcional Completo",
            "3. Interacción de Componentes UI", 
            "4. Validación de Datos y Reglas",
            "5. Casos de Borde y Errores"
        ]
        
        html_parts = []
        
        for i, section in enumerate(sections[:5]):  # Máximo 5 secciones
            # Título de la sección
            title = section_titles[i] if i < len(section_titles) else f"{i+1}. Criterio Adicional"
            html_parts.append(f"<h3>{title}</h3>")
            
            # Contenido de la sección
            section_html = self._format_section_content(section)
            html_parts.append(f"<p>{section_html}</p>")
        
        return ''.join(html_parts)

    def _extract_functionality(self, text: str) -> str:
        """
        Extrae la descripción de funcionalidad del texto
        """
        # Buscar patrón "Como... quiero... para..."
        story_pattern = r'(?:\*\*)?Como(?:\*\*)?\s+([^,]+)(?:,\s*)?(?:\*\*)?quiero(?:\*\*)?\s+([^,]+)(?:,\s*)?(?:\*\*)?para(?:\*\*)?\s+([^.]+)'
        match = re.search(story_pattern, text, re.IGNORECASE | re.DOTALL)
        
        if match:
            role, want, purpose = match.groups()
            return f"Como {role.strip()}, quiero {want.strip()}, para {purpose.strip()}."
        
        # Buscar líneas que describan funcionalidad
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if len(line) > 30 and any(keyword in line.lower() for keyword in ['permite', 'funcionalidad', 'usuario', 'registr', 'google']):
                # Limpiar markdown
                line = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)
                line = re.sub(r'^#+\s*', '', line)
                return line
        
        return ""

    def _extract_user_role(self, text: str) -> str:
        """
        Extrae el rol del usuario del texto
        """
        # Buscar patrones de rol
        role_patterns = [
            r'(?:User Role|Rol del usuario)[:]\s*([^.\n]+)',
            r'(?:\*\*)?Como(?:\*\*)?\s+([^,]+)',
            r'usuario\s+(nuevo|existente|registrado)'
        ]
        
        for pattern in role_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                role = match.group(1).strip()
                role = re.sub(r'\*\*([^*]+)\*\*', r'\1', role)  # Limpiar markdown
                return role
        
        return "Usuario del sistema"

    def _extract_user_flow(self, text: str) -> list:
        """
        Extrae los pasos del flujo de usuario
        """
        # Buscar pasos numerados
        steps = re.findall(r'(\d+)\.\s*([^.\n]+(?:\.[^0-9\n][^.\n]*)*)', text)
        
        if steps:
            flow_steps = []
            for num, step_text in steps:
                # Limpiar el paso
                step_text = step_text.strip()
                step_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', step_text)
                if len(step_text) > 10:
                    flow_steps.append(step_text)
            return flow_steps
        
        return []

    def _find_first_meaningful_paragraph(self, text: str) -> str:
        """
        Encuentra el primer párrafo significativo del texto
        """
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            # Limpiar markdown
            line = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)
            line = re.sub(r'^#+\s*', '', line)
            
            # Debe ser suficientemente largo y contener palabras clave
            if (len(line) > 20 and 
                any(keyword in line.lower() for keyword in ['permite', 'funcional', 'usuario', 'sistema']) and
                not any(skip in line.lower() for skip in ['evaluación', 'impacto', 'puntuación'])):
                return line
        
        return ""

    def _group_criteria_sections(self, lines: list) -> list:
        """
        Agrupa las líneas de criterios en secciones
        """
        sections = []
        current_section = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detectar nueva sección
            is_new_section = (
                line.startswith('###') or
                line.startswith('##') or
                re.match(r'^\d+\.\s+[A-Z]', line) or
                any(keyword in line.lower() for keyword in [
                    'intención macro', 'flujo funcional', 'interacción', 
                    'validación', 'casos de borde', 'casos límite'
                ])
            )
            
            if is_new_section and current_section:
                sections.append(current_section)
                current_section = []
            
            current_section.append(line)
        
        if current_section:
            sections.append(current_section)
        
        return sections

    def _format_section_content(self, section_lines: list) -> str:
        """
        Formatea el contenido de una sección como HTML
        """
        formatted_parts = []
        
        for line in section_lines:
            # Limpiar línea
            line = line.strip()
            if not line:
                continue
            
            # Limpiar títulos de sección
            line = re.sub(r'^#+\s*', '', line)
            line = re.sub(r'^\d+\.\s*', '', line)
            
            # Formatear palabras clave de Gherkin
            line = re.sub(r'\b(Escenario|escenario)\b\s*:?', '<strong>Escenario:</strong>', line)
            line = re.sub(r'\b(Dado|dado)\b\s+que', '<strong>Dado</strong> que', line)
            line = re.sub(r'\b(Cuando|cuando)\b\s+', '<strong>Cuando</strong> ', line)
            line = re.sub(r'\b(Entonces|entonces)\b\s+', '<strong>Entonces</strong> ', line)
            line = re.sub(r'\b(Y|y)\b\s+(?=\w)', '<strong>Y</strong> ', line)
            line = re.sub(r'(ModoVerificación|Modo de Verificación)\s*:?\s*', '<strong>ModoVerificación:</strong> ', line)
            
            # Limpiar markdown restante
            line = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', line)
            
            formatted_parts.append(line)
        
        content = '<br>'.join(formatted_parts)
        
        # Asegurar que tenga ModoVerificación
        if 'ModoVerificación' not in content:
            content += '<br><strong>ModoVerificación:</strong> Manual'
        
        return content

    def _generate_default_criteria_html(self) -> str:
        """
        Genera HTML de criterios por defecto cuando no se puede parsear el contenido
        """
        return """<h3>1. Intención Macro (Propuesta de Valor)</h3>
    <p><strong>Escenario:</strong> Registro exitoso con Google<br>
    <strong>Dado</strong> que el usuario accede a la página de registro<br>
    <strong>Cuando</strong> hace clic en "Iniciar Sesión con Google"<br>
    <strong>Entonces</strong> debe ser redirigido para autenticarse<br>
    <strong>Y</strong> completar el proceso de registro<br>
    <strong>ModoVerificación:</strong> Manual</p>

    <h3>2. Flujo Funcional Completo</h3>
    <p><strong>Escenario:</strong> Proceso completo de autenticación<br>
    <strong>Dado</strong> que el usuario inicia el proceso de registro<br>
    <strong>Cuando</strong> completa la autenticación con Google<br>
    <strong>Entonces</strong> el sistema debe crear su cuenta<br>
    <strong>Y</strong> redirigirlo al dashboard<br>
    <strong>ModoVerificación:</strong> Manual</p>

    <h3>3. Interacción de Componentes UI</h3>
    <p><strong>Escenario:</strong> Botón de Google funcional<br>
    <strong>Dado</strong> que el usuario está en la página de login<br>
    <strong>Cuando</strong> ve el botón de Google<br>
    <strong>Entonces</strong> debe estar visible y ser clickeable<br>
    <strong>ModoVerificación:</strong> Manual</p>"""

    def clean_html(self, html_string: str) -> str:
        if not html_string:
            return ""
        cleaned = re.sub(r'<[^>]+>', '', html_string)
        return cleaned.strip()
    
    def extract_feature_from_azure(self, fields: dict) -> dict:
        """
        Extrae feature y módulo directamente de los campos de Azure DevOps
        """
        # Opciones de campos donde podría estar la información del feature/módulo
        feature_fields = [
            'System.AreaPath',           # Área del proyecto
            'Microsoft.VSTS.Common.ValueArea',  # Value Area
            'Custom.Feature',            # Campo personalizado Feature
            'System.Tags',               # Tags pueden contener info del módulo
            'System.BoardColumn',        # Columna del board
            'System.BoardLane'           # Lane del board
        ]
        
        feature = None
        module = None
        
        # Buscar en diferentes campos
        area_path = fields.get('System.AreaPath', '')
        if area_path:
            # Extraer feature y módulo del area path
            # Ejemplo: "Proyecto\\Gestión de Productos\\Catálogo"
            path_parts = area_path.split('\\')
            if len(path_parts) >= 2:
                module = path_parts[1] if len(path_parts) > 1 else None
                feature = path_parts[2] if len(path_parts) > 2 else path_parts[1]
        
        # Buscar en tags
        tags = fields.get('System.Tags', '')
        if tags and not feature:
            # Los tags pueden contener "Feature:NombreFeature;Module:NombreModule"
            tag_parts = tags.split(';')
            for tag in tag_parts:
                if 'feature' in tag.lower():
                    feature = tag.split(':')[-1].strip() if ':' in tag else tag.strip()
                elif 'module' in tag.lower() or 'módulo' in tag.lower():
                    module = tag.split(':')[-1].strip() if ':' in tag else tag.strip()
        
        # Buscar en Value Area
        value_area = fields.get('Microsoft.VSTS.Common.ValueArea', '')
        if value_area and not module:
            module = value_area
        
        return {
            'feature': feature or "Sin Feature",
            'module': module or "Sin Módulo"
        }
    
    def fetch_hu(self, azure_id: str) -> dict:
        try:
            azure_id_num = int(azure_id)
        except ValueError:
            raise Exception(f"Azure ID must be a number, got: {azure_id}")
        
        # ✅ MEJORADO: Expandir más campos para obtener toda la información
        url = f"https://dev.azure.com/{self.org}/{self.project}/_apis/wit/workitems?ids={azure_id_num}&$expand=all&api-version=7.1"
        
        print(f"🔍 Fetching work item {azure_id_num} from Azure DevOps...")
        response = requests.get(url, headers=self.headers)
        
        if response.status_code != 200:
            print(f"❌ Azure DevOps API error: {response.status_code}")
            print(f"Response: {response.text}")
            raise Exception(f"Failed to fetch HU from Azure DevOps: {response.status_code}")
        
        data = response.json()
        if not data.get('value'):
            raise Exception(f"No work item found with ID: {azure_id}")
        
        work_item = data['value'][0]
        fields = work_item.get('fields', {})
        
        print(f"📋 Work item fields found: {list(fields.keys())}")
        
        # ✅ MEJORADO: Obtener feature y módulo dinámicamente
        feature_info = self.extract_feature_from_azure(fields)
        
        # ✅ MEJORADO: Obtener más información del work item
        title = fields.get('System.Title', '')
        description = self.clean_html(fields.get('System.Description', ''))
        acceptance_criteria = self.clean_html(fields.get('Microsoft.VSTS.Common.AcceptanceCriteria', ''))
        
        # Información adicional que puede ser útil
        work_item_type = fields.get('System.WorkItemType', 'User Story')
        state = fields.get('System.State', 'New')
        priority = fields.get('Microsoft.VSTS.Common.Priority', '')
        
        print(f"✅ Work item details:")
        print(f"   Title: {title}")
        print(f"   Type: {work_item_type}")
        print(f"   State: {state}")
        print(f"   Feature: {feature_info['feature']}")
        print(f"   Module: {feature_info['module']}")
        print(f"   Description length: {len(description)} chars")
        print(f"   Acceptance criteria length: {len(acceptance_criteria)} chars")
        
        return {
            'id': work_item.get('id'),
            'title': title,
            'description': description,
            'acceptanceCriteria': acceptance_criteria,
            'feature': feature_info['feature'],
            'module': feature_info['module'],
            'workItemType': work_item_type,
            'state': state,
            'priority': priority
        }

    def update_hu_in_azure(self, azure_id: str, refined_response: str, markdown_response: str) -> bool:
        """
        Actualiza una Historia de Usuario en Azure DevOps con los criterios refinados
        ENVIANDO HTML FORMATEADO
        """
        try:
            azure_id_num = int(azure_id)
        except ValueError:
            raise Exception(f"Azure ID must be a number, got: {azure_id}")
        
        print(f"🔄 Starting Azure DevOps HTML update for work item {azure_id_num}")
        print(f"   📊 Organization: {self.org}")
        print(f"   📂 Project: {self.project}")
        
        # ✅ NUEVO: Parsear el contenido refinado a HTML
        parsed_content = self.parse_refined_content(refined_response)
        description_html = parsed_content['description']
        criteria_html = parsed_content['acceptance_criteria']
        
        print(f"🎨 HTML content for Azure DevOps:")
        print(f"   📝 Description HTML: {len(description_html)} characters")
        print(f"   ✅ Acceptance Criteria HTML: {len(criteria_html)} characters")
        
        # Mostrar preview del HTML
        desc_preview = description_html[:300] + "..." if len(description_html) > 300 else description_html
        criteria_preview = criteria_html[:300] + "..." if len(criteria_html) > 300 else criteria_html
        
        print(f"   🎨 Description HTML preview:")
        print(f"   {desc_preview}")
        print(f"   🎨 Criteria HTML preview:")
        print(f"   {criteria_preview}")
        
        # ✅ PASO 1: Obtener la revisión actual del work item
        get_url = f"https://dev.azure.com/{self.org}/{self.project}/_apis/wit/workitems/{azure_id_num}?api-version=7.1"
        get_response = requests.get(get_url, headers=self.headers)
        
        if get_response.status_code != 200:
            print(f"❌ Failed to GET work item: {get_response.status_code}")
            raise Exception(f"Failed to get work item revision: {get_response.status_code}")
        
        work_item = get_response.json()
        current_rev = work_item.get('rev', 1)
        current_title = work_item.get('fields', {}).get('System.Title', 'Unknown')
        
        print(f"✅ Work item retrieved: {current_title} (rev: {current_rev})")
        
        # ✅ PASO 2: Preparar los datos para actualizar con HTML
        update_url = f"https://dev.azure.com/{self.org}/{self.project}/_apis/wit/workitems/{azure_id_num}?api-version=7.1"
        
        patch_headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json-patch+json",
            "Accept": "application/json"
        }
        
        from datetime import datetime, timezone
        current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # ✅ CORREGIDO: Enviar HTML formateado
        patch_document = [
            {
                "op": "test",
                "path": "/rev",
                "value": current_rev
            },
            {
                "op": "replace",
                "path": "/fields/System.Description",
                "value": description_html  # ✅ HTML formateado para descripción
            },
            {
                "op": "replace",
                "path": "/fields/Microsoft.VSTS.Common.AcceptanceCriteria",
                "value": criteria_html  # ✅ HTML formateado para criterios
            },
            {
                "op": "add",
                "path": "/fields/System.Tags",
                "value": "QA-Refinado;Aprobado;HTML-Formatted"
            },
            {
                "op": "add",
                "path": "/fields/System.History",
                "value": f"<p><strong>Historia de Usuario refinada y aprobada por QA automáticamente.</strong></p><p>Fecha: {current_time}</p><p>Formato: HTML con etiquetas semánticas para mejor visualización.</p>"
            }
        ]
        
        print(f"🔧 Sending PATCH with HTML formatted content...")
        
        # ✅ PASO 3: Enviar la petición PATCH
        try:
            response = requests.patch(update_url, headers=patch_headers, json=patch_document, timeout=30)
            
            print(f"📨 Response: {response.status_code}")
            
            if response.status_code == 200:
                updated_work_item = response.json()
                new_rev = updated_work_item.get('rev', 'Unknown')
                
                print(f"✅ Work item {azure_id_num} updated successfully with HTML formatting!")
                print(f"   📊 New revision: {new_rev} (was {current_rev})")
                print(f"   🎨 HTML Description: {len(description_html)} chars")
                print(f"   🎨 HTML Criteria: {len(criteria_html)} chars")
                
                if new_rev != current_rev:
                    print(f"✅ CONFIRMED: HTML content updated correctly in Azure DevOps")
                    return True
                else:
                    print(f"⚠️ WARNING: Revision didn't change")
                    return False
                    
            else:
                print(f"❌ Failed to update: {response.status_code}")
                print(f"❌ Response: {response.text}")
                raise Exception(f"Failed to update Azure DevOps work item: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error updating Azure DevOps: {str(e)}")
            raise