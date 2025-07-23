# Feature mapping (igual que en Node.js)
FEATURE_MAPPING = {
    # Gestión de Información
    'F-102': {
        'name': 'Perfil de Usuario',
        'module': 'Gestión de Información',
        'hus': [109, 110, 202]
    },
    'F-100': {
        'name': 'Registro, login, validación y recuperar contraseña',
        'module': 'Gestión de Información',
        'hus': [129, 303, 360]
    },
    'F-373': {
        'name': 'Gestión de perfil e historial del repartidor',
        'module': 'Gestión de Información',
        'hus': [374, 375, 376]
    },
    # Gestión de Productos
    'F-97': {
        'name': 'Gestión de Lotes y Productos',
        'module': 'Gestión de Productos',
        'hus': [103, 104, 177, 200, 207]
    },
    'F-99': {
        'name': 'Catálogo de Productos e Interacción Visual',
        'module': 'Gestión de Productos',
        'hus': [246, 247, 248]
    },
    'F-249': {
        'name': 'Detalle de Productos y Agregado al Carrito',
        'module': 'Gestión de Productos',
        'hus': [117, 253]
    },
    'F-252': {
        'name': 'Navegación por Categorías y Búsqueda Flotante',
        'module': 'Gestión de Productos',
        'hus': [107, 116, 208]
    },
    # Gestión de Pedidos
    'F-138': {
        'name': 'Gestión de estados',
        'module': 'Gestión de Pedidos',
        'hus': [114]
    },
    'F-255': {
        'name': 'Carrito y Checkout del Dropshipper',
        'module': 'Gestión de Pedidos',
        'hus': [126, 132, 204]
    },
    # Gestión de Métricas
    'F-133': {
        'name': 'Dashboard Principal',
        'module': 'Gestión de Métricas',
        'hus': [135, 136, 137, 203, 309, 310]
    }
}

def get_feature_info(azure_id_num: int) -> dict:
    """Busca la información de feature y módulo basado en el azure_id"""
    for feature_id, feature_info in FEATURE_MAPPING.items():
        if azure_id_num in feature_info['hus']:
            return {
                'feature': feature_info['name'],
                'module': feature_info['module'],
                'feature_id': feature_id
            }
    return {'feature': None, 'module': None, 'feature_id': None}