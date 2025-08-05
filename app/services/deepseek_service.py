import os
import json
import requests
from typing import Tuple
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class DeepSeekService:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://blackbird-labs.com",
            "X-Title": "RIWI QA Backend"
        }
    
    def refine_hu(self, title: str, description: str, acceptance_criteria: str = "", feature: str = "", module: str = "", language: str = "es") -> Tuple[str, str]:
        if not title or len(title.strip()) < 5:
            raise Exception("El título de la HU es muy corto o está vacío")
        
        print(f"🤖 Refinando HU con calidad completa:")
        print(f"   📝 Título: {title}")
        print(f"   📄 Descripción: {len(description)} caracteres")
        print(f"   🏷️ Feature: {feature}")
        print(f"   📦 Módulo: {module}")
        print(f"   🌐 Idioma: {language}")
        
        # Seleccionar el prompt según el idioma
        if language == "en":
            print("🔄 Translating input fields to English...")
            title = self._translate_to_english(title)
            description = self._translate_to_english(description)
            acceptance_criteria = self._translate_to_english(acceptance_criteria)
            feature = self._translate_to_english(feature)
            module = self._translate_to_english(module)
            prompt = self._get_english_prompt(title, description, acceptance_criteria, feature, module)
            print(f"🔍 DEBUG: Usando prompt en INGLÉS")
        else:
            prompt = self._get_spanish_prompt(title, description, acceptance_criteria, feature, module)
            print(f"🔍 DEBUG: Usando prompt en ESPAÑOL")
        
        print(f"🔍 DEBUG: Prompt seleccionado (primeros 200 chars):")
        print(f"   {prompt[:200]}...")
        
        payload = {
            "model": "openrouter/horizon-beta",  # Cambiar a un modelo más neutral
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 8000,
            "temperature": 0.3
        }
        
        print(f"🚀 Enviando request de alta calidad a Gemma...")
        print(f"   📊 Max tokens: {payload['max_tokens']}")
        print(f"   📝 Prompt length: {len(prompt)} characters")
        print(f"   🌐 Language: {language}")
        
        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=90)
            
            if response.status_code != 200:
                print(f"❌ Gemma API error: {response.status_code}")
                print(f"❌ Response: {response.text}")
                raise Exception(f"Gemma API error: {response.status_code}")
            
            result = response.json()
            
            if 'choices' not in result or not result['choices']:
                raise Exception("Invalid API response format")
            
            content = result['choices'][0]['message']['content']
            
            print(f"✅ Gemma response received:")
            print(f"   📏 Content length: {len(content)} characters")
            
            print(f"   📄 Content preview (primeros 500 chars):")
            print(f"   {content[:500]}...")
            
            # Debug: Verificar si la respuesta está en inglés
            print(f"🔍 DEBUG: Verificando idioma de la respuesta:")
            if 'EVALUACIÓN AUTOMÁTICA DE CRITICIDAD' in content[:1000]:
                print(f"   ⚠️  La IA respondió en ESPAÑOL aunque se solicitó {language.upper()}")
                # Si se solicitó inglés pero la IA respondió en español, traducir
                if language == "en":
                    print(f"   🔄 Traduciendo contenido de español a inglés...")
                    content = self._translate_to_english(content)
                    print(f"   ✅ Contenido traducido a inglés")
            elif 'AUTOMATIC CRITICALITY ASSESSMENT' in content[:1000]:
                print(f"   ✅ La IA respondió en INGLÉS correctamente")
            else:
                print(f"   ❓ No se puede determinar el idioma de la respuesta")
            
            possible_plain_markers = [
                "## CONSIDERACIONES TÉCNICAS",
                "## CRITERIOS DE DONE",
                "## TECHNICAL CONSIDERATIONS",
                "## DONE CRITERIA",
                "CONSIDERACIONES TÉCNICAS",
                "CRITERIOS DE DONE"
            ]
            
            plain_text_start = -1
            
            for marker in possible_plain_markers:
                pos = content.find(marker)
                if pos != -1:
                    plain_text_start = pos
                    print(f"   ✅ Found separator marker: '{marker}' at position {pos}")
                    break
            
            print(f"   📍 Separator position: {plain_text_start}")
            
            plain_text = content.strip()
            markdown_text = content.strip()
            
            print(f"✅ Using full content for both fields:")
            print(f"   📝 Plain text: {len(plain_text)} characters")
            print(f"   📋 Markdown: {len(markdown_text)} characters")
            
            if len(plain_text) < 1000:
                print(f"⚠️ WARNING: Contenido muy corto ({len(plain_text)} chars)")
                if language == "en":
                    fallback = f"""
## AUTOMATIC CRITICALITY ASSESSMENT
**Business Impact**: 4/5 - Important functionality for the business
**Usage Frequency**: 3/5 - Regular use by users  
**Technical Complexity**: 3/5 - Medium complexity implementation
**Failure Impact**: 4/5 - Failure would significantly affect users
**Novelty**: 2/5 - Known functionality with established patterns
**TOTAL SCORE**: 16/25
**CLASSIFICATION**: 🟠 HIGH

## REFINED USER STORY
{title}

{content}

## TECHNICAL CONSIDERATIONS
- Implement client and server-side validations
- Consider performance for large data volumes
- Ensure compatibility with different browsers

## DONE CRITERIA
- Functionality implemented and tested
- Validations working correctly
- Documentation updated
"""
                else:
                    fallback = f"""
## EVALUACIÓN AUTOMÁTICA DE CRITICIDAD
**Impacto Negocio**: 4/5 - Funcionalidad importante para el negocio
**Frecuencia Uso**: 3/5 - Uso regular por parte de los usuarios  
**Complejidad Técnica**: 3/5 - Implementación de complejidad media
**Impacto de Falla**: 4/5 - Falla afectaría significativamente a los usuarios
**Novedad**: 2/5 - Funcionalidad conocida con patrones establecidos
**PUNTUACIÓN TOTAL**: 16/25
**CLASIFICACIÓN**: 🟠 ALTA

## HISTORIA DE USUARIO REFINADA
{title}

{content}

## CONSIDERACIONES TÉCNICAS
- Implementar validaciones del lado cliente y servidor
- Considerar rendimiento para grandes volúmenes de datos
- Asegurar compatibilidad con diferentes navegadores

## CRITERIOS DE DONE
- Funcionalidad implementada y probada
- Validaciones funcionando correctamente
- Documentación actualizada
"""
                plain_text = fallback
                markdown_text = fallback
            
            return plain_text, markdown_text
            
        except Exception as e:
            print(f"❌ Error during refinement: {str(e)}")
            raise Exception(f"Error durante el refinamiento: {str(e)}")
    
    def _get_spanish_prompt(self, title: str, description: str, acceptance_criteria: str, feature: str, module: str) -> str:
        """Genera el prompt en español"""
        return f"""Eres un experto en Refinamiento de User Stories y QA con más de 10 años de experiencia. Tu tarea es refinar la siguiente historia de usuario aplicando metodología de evaluación de criticidad y generando criterios de aceptación en formato Gherkin.

**INFORMACIÓN DE LA HISTORIA DE USUARIO:**
- **Título**: {title}
- **Descripción**: {description if description else "No se proporcionó descripción detallada"}
- **Criterios originales**: {acceptance_criteria if acceptance_criteria else "No se proporcionaron criterios originales"}
- **Feature/Épica**: {feature if feature else "No especificada"}
- **Módulo del Sistema**: {module if module else "No especificado"}

**INSTRUCCIONES CRÍTICAS:**
1. DEBES generar una respuesta COMPLETA y DETALLADA de al menos 3000 caracteres
2. NUNCA generes respuestas cortas o ambiguas
3. SIEMPRE incluye los 5 niveles de criterios de aceptación
4. CADA criterio debe ser específico, medible y testeable
5. Esta información será enviada a Azure DevOps para que los desarrolladores y testers la usen

**INSTRUCCIONES CRÍTICAS PARA MÚLTIPLES ESCENARIOS:**
1. **MÍNIMO 3 ESCENARIOS POR CADA CRITERIO DE ACEPTACIÓN** - No negociable
2. **MÁXIMO ILIMITADO** - Genera tantos escenarios como consideres necesarios para cobertura completa
3. **DIVERSIDAD OBLIGATORIA** - Cada escenario debe cubrir un aspecto diferente (positivo, negativo, edge case, diferentes roles, etc.)
4. **COBERTURA EXHAUSTIVA** - Piensa en todos los posibles caminos, condiciones y casos de uso
5. **RESPUESTA ULTRA-DETALLADA** - Mínimo 5000 caracteres de contenido rico

**METODOLOGÍA DE GENERACIÓN DE ESCENARIOS:**
- **Escenario Principal**: Happy path, flujo ideal
- **Escenarios Alternativos**: Diferentes caminos válidos
- **Escenarios de Validación**: Reglas de negocio, restricciones
- **Escenarios de Error**: Casos negativos, fallos esperados
- **Escenarios Edge**: Casos límite, condiciones extremas
- **Escenarios de Roles**: Diferentes tipos de usuarios
- **Escenarios de Estado**: Diferentes estados del sistema
- **Escenarios de Integración**: Interacciones con otros componentes


**PROCESO OBLIGATORIO:**

1. **EVALÚA LA CRITICIDAD** (5 criterios de 1-5):
   - Impacto Negocio: ¿Qué tan crítico es para el negocio?
   - Frecuencia Uso: ¿Qué tan seguido se usa?
   - Complejidad Técnica: ¿Qué tan complejo es implementar?
   - Impacto de Falla: ¿Qué tan grave es si falla?
   - Novedad: ¿Qué tan nueva es la funcionalidad?

2. **APLICA ESTRATEGIA SEGÚN CRITICIDAD:**
   - 🔴 CRÍTICA (20-25 pts): Cobertura exhaustiva con casos edge
   - 🟠 ALTA (16-19 pts): Cobertura optimizada con validaciones
   - 🟡 MEDIA (11-15 pts): Cobertura básica con flujo principal
   - 🟢 BAJA (5-10 pts): Cobertura mínima pero completa

3. **GENERA CRITERIOS DETALLADOS EN 5 NIVELES OBLIGATORIOS:**

## EVALUACIÓN AUTOMÁTICA DE CRITICIDAD
**Impacto Negocio**: [X]/5 - [Justificación detallada de por qué este puntaje]
**Frecuencia Uso**: [X]/5 - [Justificación detallada de por qué este puntaje]
**Complejidad Técnica**: [X]/5 - [Justificación detallada de por qué este puntaje]
**Impacto de Falla**: [X]/5 - [Justificación detallada de por qué este puntaje]
**Novedad**: [X]/5 - [Justificación detallada de por qué este puntaje]
**PUNTUACIÓN TOTAL**: [X]/25
**CLASIFICACIÓN**: 🔴/🟠/🟡/🟢 [CRÍTICA/ALTA/MEDIA/BAJA]
**ESTRATEGIA**: [Descripción detallada del enfoque de testing y cobertura]

## HISTORIA DE USUARIO REFINADA
**Como** [rol específico], **quiero** [funcionalidad detallada], **para** [valor/beneficio concreto y medible].

**User Role:** [Definir claramente el rol del usuario]
**Business Value:** [Explicar el valor de negocio específico]

**Pasos o User Flow Detallado:**
1. [Paso 1 - Acción específica del usuario]
2. [Paso 2 - Respuesta del sistema]
3. [Paso 3 - Validación o confirmación]
4. [Paso 4 - Resultado final]
5. [Pasos adicionales si son necesarios]

## CRITERIOS DE ACEPTACIÓN DETALLADOS

### 1. Intención Macro (Propuesta de Valor)
**Escenario**: [Descripción clara del escenario de valor principal]
**Dado** que [condición inicial específica y medible]
**Cuando** [acción del usuario detallada]
**Entonces** [resultado esperado específico y verificable]
**Y** [condiciones adicionales de éxito]
**ModoVerificación**: [Manual/Automático con detalles específicos]

### 2. Flujo Funcional Completo
**Escenario**: [Descripción del flujo end-to-end completo]
**Dado** que [precondición del sistema y datos]
**Cuando** [secuencia de acciones paso a paso]
**Entonces** [resultado del flujo completo]
**Y** [validaciones de integridad de datos]
**Y** [confirmaciones de estado del sistema]
**ModoVerificación**: [Manual/Automático con casos de prueba específicos]

### 3. Interacción con Componentes de Interfaz
**Escenario**: [Descripción detallada de la interacción UI/UX]
**Dado** que [estado específico de la interfaz]
**Cuando** [interacción específica del usuario]
**Entonces** [comportamiento esperado de la UI]
**Y** [cambios visuales específicos]
**Y** [feedback al usuario]
**ModoVerificación**: [Manual con casos de usabilidad específicos]

### 4. Validación de Datos y Reglas de Negocio
**Escenario**: [Descripción de todas las validaciones necesarias]
**Dado** que [datos de entrada específicos]
**Cuando** [validación ejecutada por el sistema]
**Entonces** [resultado de validación específico]
**Y** [manejo de errores detallado]
**Y** [mensajes de error específicos]
**ModoVerificación**: [Automático con casos de prueba de validación]

### 5. Casos Límite y Manejo de Errores
**Escenario**: [Descripción de casos edge y errores]
**Dado** que [condición límite específica]
**Cuando** [acción en caso límite]
**Entonces** [comportamiento esperado del sistema]
**Y** [manejo graceful de errores]
**Y** [logging y monitoreo de errores]
**ModoVerificación**: [Automático con casos de prueba negativos]

## CONSIDERACIONES TÉCNICAS
- [Tecnologías específicas a utilizar]
- [Patrones de diseño recomendados]
- [Consideraciones de rendimiento]
- [Aspectos de seguridad]
- [Integraciones necesarias]

## CRITERIOS DE DONE
- [Criterio técnico específico 1]
- [Criterio de testing específico 2]
- [Criterio de documentación específico 3]
- [Criterio de despliegue específico 4]
- [Criterio de validación de usuario específico 5]

**RECORDATORIO CRÍTICO**: 
- Esta respuesta DEBE ser COMPLETA y DETALLADA (mínimo 3000 caracteres)
- TODOS los criterios deben ser específicos y testeables
- NUNCA generes respuestas ambiguas o incompletas
- Esta información será usada por desarrolladores y testers
- Incluye SIEMPRE los 5 niveles de criterios de aceptación"""

    def _get_english_prompt(self, title: str, description: str, acceptance_criteria: str, feature: str, module: str) -> str:
        """Generates the full English prompt with strict instructions"""
        return f"""
            You are a senior QA engineer and expert in software refinement.

            ⚠️ VERY IMPORTANT:
            - WRITE EVERYTHING in **ENGLISH ONLY**
            - DO NOT use Spanish at all, even if the original input is in Spanish.
            - Responses in Spanish will be rejected.
            - The result will be published in a Jira ticket used by English-speaking developers.

            ---

            ## USER STORY INFORMATION:
            - **Title**: {title}
            - **Description**: {description if description else "No description provided"}
            - **Original Acceptance Criteria**: {acceptance_criteria if acceptance_criteria else "Not provided"}
            - **Feature or Epic**: {feature if feature else "Not specified"}
            - **System Module**: {module if module else "Not specified"}

            ---

            ## INSTRUCTIONS:

            1. You MUST generate a DETAILED and COMPLETE response (at least 3000 characters).
            2. NEVER return short or vague answers.
            3. ALWAYS include 5 levels of acceptance criteria using Gherkin syntax.
            4. EACH acceptance criterion must include multiple realistic test scenarios.
            5. This will be consumed by testers and developers in Azure DevOps.

            ---

            ## REQUIRED OUTPUT STRUCTURE:

            ### AUTOMATIC CRITICALITY ASSESSMENT
            **Business Impact**: [X]/5 - Justify the score clearly  
            **Usage Frequency**: [X]/5 - Justify  
            **Technical Complexity**: [X]/5 - Justify  
            **Failure Impact**: [X]/5 - Justify  
            **Novelty**: [X]/5 - Justify  
            **TOTAL SCORE**: [X]/25  
            **CLASSIFICATION**: 🔴/🟠/🟡/🟢 [Critical / High / Medium / Low]

            ---

            ### REFINED USER STORY
            As a [specific user role], I want to [detailed functionality], so that [clear, measurable value].

            Detailed user flow steps:
            1. [...]
            2. [...]
            3. [...]

            ---

            ### ACCEPTANCE CRITERIA (use Gherkin syntax)

            #### 1. Business Value Scenario
            **Scenario**: [...]
            **Given** [starting condition]
            **When** [user performs action]
            **Then** [expected result]
            **And** [...]

            #### 2. Complete Functional Flow
            **Scenario**: [...]
            **Given** [...]
            **When** [...]
            **Then** [...]
            **And** [...]

            #### 3. UI Interaction
            ...

            #### 4. Data Validation
            ...

            #### 5. Edge Cases & Error Handling
            ...

            ---

            ### TECHNICAL CONSIDERATIONS
            - [...technical constraints, architecture notes...]

            ### DONE CRITERIA
            - All flows implemented and tested
            - Validations confirmed
            - Documentation updated
        """

    
    def re_refine_hu(self, feedback: str, original_response: str) -> tuple:
        prompt = f"""Eres un experto en Refinamiento de User Stories y QA. Tu tarea es RE-REFINAR una historia de usuario que fue RECHAZADA por un QA. Debes aplicar específicamente el feedback recibido para corregir los problemas identificados.

**HISTORIA DE USUARIO ORIGINAL REFINADA:**
{original_response}

**FEEDBACK DEL QA (MOTIVO DE RECHAZO):**
{feedback}

**PROCESO DE RE-REFINAMIENTO:**

1. **ANALIZA EL FEEDBACK DEL QA:**
   - Lee cuidadosamente cada observación del QA
   - Identifica los problemas específicos señalados
   - Determina qué secciones necesitan corrección

2. **APLICA LAS CORRECCIONES ESPECÍFICAS:**
   - Corrige cada punto mencionado en el feedback
   - Mantén todo lo que NO fue criticado
   - Mejora solo las áreas problemáticas identificadas

3. **CONSERVA LA ESTRUCTURA EXITOSA:**
   - Mantén el formato Gherkin y estructura de 5 niveles
   - Preserva la evaluación de criticidad si no fue cuestionada
   - Conserva los aspectos que funcionaron bien

**FORMATO DE SALIDA REQUERIDO:**

## ANÁLISIS DEL FEEDBACK DEL QA
**Problemas identificados por el QA:**
- [Problema 1 específico del feedback]
- [Problema 2 específico del feedback]
- [Problema 3 específico del feedback]

**Correcciones aplicadas:**
- [Corrección 1 para abordar el problema 1]
- [Corrección 2 para abordar el problema 2]
- [Corrección 3 para abordar el problema 3]

---

## HISTORIA DE USUARIO CORREGIDA
[Mantén la estructura original pero corrige según el feedback]

**IMPORTANTE: Solo modifica las secciones que el QA señaló como problemáticas. Mantén todo lo demás igual.**

---

## FORMATO TEXTO PLANO
[Resumen conciso de los criterios corregidos en texto plano]

## FORMATO MARKDOWN
[Versión formateada en Markdown corregida]

**INSTRUCCIONES CRÍTICAS**: 
- SOLO cambia lo que el QA específicamente criticó
- NO re-hagas toda la historia de usuario
- APLICA cada sugerencia del feedback de manera directa
- MANTÉN la estructura y formato original
- CONSERVA todo lo que no fue mencionado como problemático"""

        payload = {
            "model": "openrouter/horizon-beta",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 8000,
            "temperature": 0.3
        }
        
        print(f"🤖 Re-refining with Gemma using compatible configuration...")
        response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=90)
        
        if response.status_code != 200:
            print(f"❌ Gemma API error: {response.status_code} - {response.text}")
            raise Exception(f"Gemma API error: {response.status_code}")
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        print(f"✅ Re-refinement completed with {len(content)} characters")
        
        try:
            plain_text_start = content.find("## FORMATO TEXTO PLANO")
            markdown_start = content.find("## FORMATO MARKDOWN")
            
            if plain_text_start != -1 and markdown_start != -1:
                plain_text = content[plain_text_start + len("## FORMATO TEXTO PLANO"):markdown_start].strip()
                markdown_text = content[markdown_start + len("## FORMATO MARKDOWN"):].strip()
            else:
                plain_text = content
                markdown_text = content
        except Exception as e:
            print(f"⚠️ Error parsing response sections: {e}")
            plain_text = content
            markdown_text = content
        
        return plain_text, markdown_text    

    def generate_xray_tests(self, refined_response: str, xray_path: str, azure_id: str) -> dict:
        """
        Genera casos de test en formato XRay basados en la respuesta refinada de la HU
        y los clasifica automáticamente por criticidad si la IA no los clasifica
        CON REINTENTOS AUTOMÁTICOS Y MANEJO ROBUSTO DE ERRORES
        """
        
        # Extraer el número de HU para usar en la carpeta
        hu_number = azure_id.replace('HU-', '') if 'HU-' in azure_id else azure_id
        
        # Extraer solo los escenarios del contenido completo
        simplified_content = self._extract_scenarios_for_xray(refined_response)
        
        prompt = f"""
You are an expert test case generator for XRay.

Your task is to convert each of the provided scenarios into a manual test case in JSON format.

---

## INSTRUCTIONS:

1. Each scenario is labeled with a tag like:
   - "**Main Scenario:**"
   - "**Alternative Scenario:**"
   - "**Edge Scenario:**"

2. For each scenario:
   - Extract the scenario name (the bold title).
   - Convert the steps DADO, CUANDO, ENTONCES into test steps.
   - Use the scenario name as the `summary`.
   - Assign priority and folder based on type:
     - Main → "High" and folder "{xray_path}/Criticos"
     - Alternative → "Medium" and folder "{xray_path}/Importantes"
     - Edge → "Low" and folder "{xray_path}/Opcionales"

3. Use the following EXACT format for each test:

{{
  "testtype": "Manual",
  "fields": {{
    "summary": "[Scenario name]",
    "description": "[Test description extracted from the scenario]",
    "project": {{ "key": "DEUN" }},
    "issuetype": {{ "name": "Test" }},
    "priority": {{ "name": "[High|Medium|Low]" }}
  }},
  "steps": [
    {{ "action": "[DADO step]", "data": "", "result": "[ENTONCES step]" }}
  ],
  "xray_test_repository_folder": "[RUTA_XRAY]",
  "xray_test_sets": ["DEUN-319"]
}}

---

## SCENARIOS:

{simplified_content}

---

🔁 IMPORTANT: Return a JSON object exactly like this, grouping tests by category:

{{
  "criticos": [ ... ],
  "importantes": [ ... ],
  "opcionales": [ ... ]
}}

❌ DO NOT include comments, explanations, markdown, or code block formatting like ```json.  
✅ ONLY return the JSON object.
"""
        payload = {
            "model": "openrouter/horizon-beta", 
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 8000,
            "temperature": 0.2  # Menos creatividad para más precisión en formato JSON
        }

        print(f"🧪 Generando casos de test para {azure_id}...")
        print(f"   📂 Ruta XRay: {xray_path}")
        print(f"   📏 Contenido refinado: {len(refined_response)} caracteres")

        # ✅ CONFIGURACIÓN DE REINTENTOS
        max_attempts = 3
        base_timeout = 60  # Timeout inicial más alto
        
        for attempt in range(1, max_attempts + 1):
            try:
                print(f"🔄 Intento {attempt}/{max_attempts} - Conectando con IA...")
                
                # Timeout progresivo: 60s, 90s, 120s
                current_timeout = base_timeout + (attempt - 1) * 30
                print(f"   ⏱️ Timeout configurado: {current_timeout}s")
                
                # ✅ CONFIGURACIÓN ROBUSTA DE REQUESTS
                session = requests.Session()
                session.headers.update(self.headers)
                
                # Configurar adaptadores con reintentos a nivel de conexión
                from requests.adapters import HTTPAdapter
                from urllib3.util.retry import Retry
                
                retry_strategy = Retry(
                    total=2,  # Reintentos a nivel de urllib3
                    status_forcelist=[429, 500, 502, 503, 504],
                    backoff_factor=1,
                    raise_on_status=False
                )
                
                adapter = HTTPAdapter(max_retries=retry_strategy)
                session.mount("http://", adapter)
                session.mount("https://", adapter)
                
                response = session.post(
                    self.base_url, 
                    json=payload, 
                    timeout=current_timeout,
                    verify=True,  # Verificar SSL
                    stream=False  # No usar streaming
                )
                
                print(f"   📡 Respuesta recibida: {response.status_code}")
                
                if response.status_code != 200:
                    error_msg = f"API error: {response.status_code}"
                    if hasattr(response, 'text'):
                        error_msg += f" - {response.text[:200]}"
                    
                    if attempt < max_attempts:
                        print(f"❌ {error_msg}")
                        print(f"   🔄 Reintentando en {attempt * 2} segundos...")
                        import time
                        time.sleep(attempt * 2)  # Backoff exponencial
                        continue
                    else:
                        raise Exception(f"Error en API de Gemma después de {max_attempts} intentos: {error_msg}")

                result = response.json()
                
                if 'choices' not in result or not result['choices']:
                    if attempt < max_attempts:
                        print(f"❌ Formato de respuesta inválido")
                        print(f"   🔄 Reintentando en {attempt * 2} segundos...")
                        import time
                        time.sleep(attempt * 2)
                        continue
                    else:
                        raise Exception("Formato de respuesta de API inválido después de múltiples intentos")

                content = result['choices'][0]['message']['content'].strip()
                
                print(f"📝 Respuesta de IA recibida: {len(content)} caracteres")
                print(f"📄 Primeros 200 caracteres de la respuesta:")
                print(f"{content[:200]}...")
                
                # Limpiar el contenido JSON (remover markdown code blocks si existen)
                if content.startswith('```json'):
                    content = content.replace('```json', '').replace('```', '').strip()
                elif content.startswith('```'):
                    content = content.replace('```', '').strip()
                
                print(f"🧹 Contenido limpiado ({len(content)} chars)")
                
                # Intentar parsear el JSON
                try:
                    parsed_data = json.loads(content)
                    
                    print(f"📊 Tipo de respuesta recibida: {type(parsed_data)}")
                    
                    # ✅ MANEJAR AMBOS FORMATOS: Lista simple o Objeto clasificado
                    if isinstance(parsed_data, list):
                        # Formato: lista de tests sin clasificar
                        print(f"📋 IA devolvió lista de {len(parsed_data)} tests (sin clasificar). Clasificando automáticamente...")
                        
                        if len(parsed_data) == 0:
                            if attempt < max_attempts:
                                print(f"❌ No se generaron tests")
                                print(f"   🔄 Reintentando en {attempt * 2} segundos...")
                                import time
                                time.sleep(attempt * 2)
                                continue
                            else:
                                raise ValueError("No se generaron casos de test después de múltiples intentos")
                        
                        # Clasificar automáticamente los tests por posición/índice
                        total_tests = len(parsed_data)
                        criticos = []
                        importantes = []
                        opcionales = []
                        
                        # Distribución automática basada en el total de tests
                        for i, test in enumerate(parsed_data):
                            # Validar que el test sea un objeto válido
                            if not isinstance(test, dict):
                                raise ValueError(f"Test {i+1} no es un objeto válido")
                            
                            # Actualizar la ruta de cada test para incluir el subdirectorio
                            if i < (total_tests // 3):  # Primeros tests → Críticos
                                test["xray_test_repository_folder"] = f"{xray_path}/Criticos"
                                criticos.append(test)
                            elif i < (2 * total_tests // 3):  # Tests medios → Importantes
                                test["xray_test_repository_folder"] = f"{xray_path}/Importantes"  
                                importantes.append(test)
                            else:  # Últimos tests → Opcionales
                                test["xray_test_repository_folder"] = f"{xray_path}/Opcionales"
                                opcionales.append(test)
                        
                        classified_tests = {
                            "criticos": criticos,
                            "importantes": importantes, 
                            "opcionales": opcionales
                        }
                        
                        print(f"✅ Clasificación automática completada:")
                        print(f"   🔴 Críticos: {len(criticos)}")
                        print(f"   🟡 Importantes: {len(importantes)}")
                        print(f"   🟢 Opcionales: {len(opcionales)}")
                        
                    elif isinstance(parsed_data, dict):
                        # Formato: objeto con categorías ya clasificado
                        print(f"✅ IA devolvió formato clasificado correctamente")
                        
                        required_categories = ['criticos', 'importantes', 'opcionales']
                        for category in required_categories:
                            if category not in parsed_data:
                                print(f"⚠️ Falta la categoría: {category}. Creando categoría vacía.")
                                parsed_data[category] = []
                            
                            if not isinstance(parsed_data[category], list):
                                print(f"⚠️ La categoría {category} no es una lista. Convirtiendo.")
                                parsed_data[category] = []
                        
                        # ✅ APLICAR TESTPATH A TODOS LOS TESTS CLASIFICADOS
                        category_paths = {
                            'criticos': f"{xray_path}/Criticos",
                            'importantes': f"{xray_path}/Importantes", 
                            'opcionales': f"{xray_path}/Opcionales"
                        }
                        
                        for category, tests in parsed_data.items():
                            if isinstance(tests, list):
                                for test in tests:
                                    if isinstance(test, dict):
                                        # Aplicar el testPath correspondiente a la categoría
                                        test["xray_test_repository_folder"] = category_paths.get(category, xray_path)
                                        print(f"   📂 Test en {category}: {test.get('fields', {}).get('summary', 'Sin nombre')} → {test['xray_test_repository_folder']}")
                        
                        classified_tests = parsed_data
                        
                    else:
                        if attempt < max_attempts:
                            print(f"❌ Formato de respuesta no válido: {type(parsed_data)}")
                            print(f"   🔄 Reintentando en {attempt * 2} segundos...")
                            import time
                            time.sleep(attempt * 2)
                            continue
                        else:
                            raise ValueError(f"Formato de respuesta no válido después de múltiples intentos: {type(parsed_data)}")
                    
                    # Contar tests por categoría (funciona para ambos casos)
                    criticos_count = len(classified_tests['criticos'])
                    importantes_count = len(classified_tests['importantes'])
                    opcionales_count = len(classified_tests['opcionales'])
                    total_tests = criticos_count + importantes_count + opcionales_count
                    
                    if total_tests == 0:
                        if attempt < max_attempts:
                            print(f"❌ No se generaron casos de test válidos")
                            print(f"   🔄 Reintentando en {attempt * 2} segundos...")
                            import time
                            time.sleep(attempt * 2)
                            continue
                        else:
                            raise ValueError("No se generaron casos de test válidos después de múltiples intentos")
                    
                    print(f"✅ {total_tests} casos de test procesados y clasificados:")
                    print(f"   🔴 Críticos: {criticos_count}")
                    print(f"   🟡 Importantes: {importantes_count}")
                    print(f"   🟢 Opcionales: {opcionales_count}")
                    
                    # Validar estructura básica de cada test en todas las categorías
                    for category_name, tests in classified_tests.items():
                        for i, test in enumerate(tests):
                            if not isinstance(test, dict):
                                raise ValueError(f"Test {i+1} en categoría {category_name} no es un objeto válido")
                            
                            required_fields = ['testtype', 'fields', 'steps', 'xray_test_repository_folder']
                            for field in required_fields:
                                if field not in test:
                                    raise ValueError(f"Test {i+1} en categoría {category_name} falta campo requerido: {field}")
                    
                    print(f"✅ Validación de estructura completada para todas las categorías")
                    print(f"✅ Generación exitosa en intento {attempt}/{max_attempts}")
                    
                    # Retornar estructura clasificada con metadatos
                    return {
                        'classified_tests': classified_tests,
                        'summary': {
                            'total_tests': total_tests,
                            'criticos': criticos_count,
                            'importantes': importantes_count,
                            'opcionales': opcionales_count
                        }
                    }
                    
                except json.JSONDecodeError as e:
                    if attempt < max_attempts:
                        print(f"❌ Error parseando JSON: {e}")
                        print(f"❌ Contenido problemático: {content[:300]}...")
                        print(f"   🔄 Reintentando en {attempt * 2} segundos...")
                        import time
                        time.sleep(attempt * 2)
                        continue
                    else:
                        print(f"❌ Error parseando JSON después de {max_attempts} intentos: {e}")
                        print(f"❌ Contenido final problemático: {content[:500]}...")
                        raise Exception(f"La IA no generó un JSON válido después de múltiples intentos: {str(e)}")
                
            except (requests.exceptions.ConnectionError, 
                    requests.exceptions.Timeout, 
                    requests.exceptions.RequestException,
                    ConnectionResetError) as e:
                
                if attempt < max_attempts:
                    print(f"❌ Error de conexión (intento {attempt}/{max_attempts}): {str(e)}")
                    print(f"   🔄 Reintentando en {attempt * 3} segundos...")
                    import time
                    time.sleep(attempt * 3)  # Backoff más largo para errores de conexión
                    continue
                else:
                    print(f"❌ Error de conexión persistente después de {max_attempts} intentos")
                    raise Exception(f"Fallo de conexión con la API después de {max_attempts} intentos: {str(e)}")
            
            except Exception as e:
                if attempt < max_attempts:
                    print(f"❌ Error inesperado (intento {attempt}/{max_attempts}): {str(e)}")
                    print(f"   🔄 Reintentando en {attempt * 2} segundos...")
                    import time
                    time.sleep(attempt * 2)
                    continue
                else:
                    print(f"❌ Error persistente después de {max_attempts} intentos: {str(e)}")
                    raise Exception(f"Fallo en generación de tests después de {max_attempts} intentos: {str(e)}")
        
        # Si llegamos aquí, todos los intentos fallaron
        raise Exception(f"Fallo en generación de tests después de {max_attempts} intentos con múltiples estrategias")
    
    def _extract_scenarios_for_xray(self, content: str) -> str:
        """Extrae solo los escenarios del contenido de la HU refinada para XRay"""
        
        import re
        
        # Buscar todos los escenarios
        scenarios = []
        
        # Patrones para encontrar escenarios
        patterns = [
            r'\*\*Escenario Principal[^*]*?\*\*[^*]*?Dado[^*]*?Cuando[^*]*?Entonces[^*]*?(?=\*\*|$)',
            r'\*\*Escenario Alternativo[^*]*?\*\*[^*]*?Dado[^*]*?Cuando[^*]*?Entonces[^*]*?(?=\*\*|$)',
            r'\*\*Escenario Edge[^*]*?\*\*[^*]*?Dado[^*]*?Cuando[^*]*?Entonces[^*]*?(?=\*\*|$)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            scenarios.extend(matches)
        
        # Si no encuentra con el patrón complejo, buscar líneas que contengan "Escenario"
        if not scenarios:
            lines = content.split('\n')
            current_scenario = ""
            in_scenario = False
            
            for line in lines:
                if "Escenario Principal" in line or "Escenario Alternativo" in line or "Escenario Edge" in line:
                    if current_scenario:
                        scenarios.append(current_scenario.strip())
                    current_scenario = line
                    in_scenario = True
                elif in_scenario and (line.strip().startswith('Dado') or line.strip().startswith('Cuando') or line.strip().startswith('Entonces') or line.strip().startswith('Y')):
                    current_scenario += "\n" + line
                elif in_scenario and line.strip() == "":
                    continue
                elif in_scenario:
                    current_scenario += "\n" + line
            
            if current_scenario:
                scenarios.append(current_scenario.strip())
        
        # Categorizar escenarios
        criticos = []
        importantes = []
        opcionales = []
        
        for scenario in scenarios:
            if "Escenario Principal" in scenario:
                criticos.append(scenario)
            elif "Escenario Alternativo" in scenario:
                importantes.append(scenario)
            elif "Escenario Edge" in scenario:
                opcionales.append(scenario)
        
        # Crear contenido simplificado
        simplified_content = "## ESCENARIOS EXTRAÍDOS\n\n"
        
        if criticos:
            simplified_content += "### ESCENARIOS PRINCIPALES\n"
            for i, scenario in enumerate(criticos, 1):
                simplified_content += f"{i}. {scenario}\n\n"
        
        if importantes:
            simplified_content += "### ESCENARIOS ALTERNATIVOS\n"
            for i, scenario in enumerate(importantes, 1):
                simplified_content += f"{i}. {scenario}\n\n"
        
        if opcionales:
            simplified_content += "### ESCENARIOS EDGE\n"
            for i, scenario in enumerate(opcionales, 1):
                simplified_content += f"{i}. {scenario}\n\n"
        
        return simplified_content

    def _translate_to_english(self, content: str) -> str:
        """Traduce el contenido de español a inglés usando la IA"""
        try:
            translation_prompt = f"""Translate the following Spanish text to English. Keep the same structure and formatting:

{content}

Translate to English:"""
            
            payload = {
                "model": "openrouter/gpt-4o-mini",
                "messages": [{"role": "user", "content": translation_prompt}],
                "max_tokens": 8000,
                "temperature": 0.1
            }
            
            print(f"🔍 DEBUG: Traduciendo contenido de español a inglés...")
            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=90)
            
            if response.status_code != 200:
                print(f"❌ Error en traducción: {response.status_code}")
                return content  # Retornar contenido original si falla
            
            result = response.json()
            translated_content = result['choices'][0]['message']['content']
            
            print(f"✅ Traducción completada")
            return translated_content
            
        except Exception as e:
            print(f"❌ Error durante traducción: {str(e)}")
            return content  # Retornar contenido original si falla
