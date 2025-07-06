"""
Configuración central para suprimir salidas no deseadas de librerías problemáticas.

Este módulo debe ser importado al inicio de cualquier archivo que use:
- argostranslate
- google.generativeai
- langdetect
- ctranslate2
- transformers
- tensorflow
"""

import os
import sys
import io
import logging
import warnings
from contextlib import redirect_stdout, redirect_stderr

def configure_logging():
    """Configura el logging para suprimir salidas de librerías problemáticas"""
    # Configurar logging para suprimir salidas de librerías de traducción
    logging.getLogger('argostranslate').setLevel(logging.CRITICAL)
    logging.getLogger('ctranslate2').setLevel(logging.CRITICAL)
    logging.getLogger('transformers').setLevel(logging.CRITICAL)
    
    # Configurar logging para suprimir salidas de Google APIs
    logging.getLogger('google.generativeai').setLevel(logging.CRITICAL)
    logging.getLogger('grpc').setLevel(logging.CRITICAL)
    logging.getLogger('google.auth').setLevel(logging.CRITICAL)
    logging.getLogger('google.api_core').setLevel(logging.CRITICAL)
    logging.getLogger('googleapiclient').setLevel(logging.CRITICAL)
    
    # Configurar logging para suprimir salidas de langdetect
    logging.getLogger('langdetect').setLevel(logging.CRITICAL)
    
    # Configurar logging para suprimir salidas de SQLAlchemy
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.orm').setLevel(logging.WARNING)
    
    # Configurar logging para recursos de la aplicación
    app_log_level = os.getenv("APP_LOG_LEVEL", "INFO").upper()
    logging.getLogger('backend.resources').setLevel(getattr(logging, app_log_level, logging.INFO))
    
    # Configurar logging básico
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def configure_warnings():
    """Configura warnings para suprimir avisos no deseados"""
    # Suprimir warnings de tensorflow/transformers
    warnings.filterwarnings('ignore', category=UserWarning)
    warnings.filterwarnings('ignore', category=FutureWarning)
    
    # Suprimir warnings específicos de Google APIs
    warnings.filterwarnings('ignore', category=UserWarning, module='google')
    warnings.filterwarnings('ignore', category=FutureWarning, module='google')
    
    # Suprimir warnings de gRPC
    warnings.filterwarnings('ignore', category=UserWarning, module='grpc')


def configure_environment():
    """Configura variables de entorno para suprimir salidas"""
    # Suprimir logs de TensorFlow
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    
    # Evitar warnings de tokenizers
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    
    # Suprimir logs de gRPC
    os.environ['GRPC_VERBOSITY'] = 'ERROR'
    os.environ['GRPC_TRACE'] = ''
    
    # Suprimir salidas de stdout/stderr
    sys.stdout.flush()
    sys.stderr.flush()


def clean_console_output():
    """Limpia la salida de la consola de caracteres extraños"""
    # Flush para asegurar que toda la salida se procese
    sys.stdout.flush()
    sys.stderr.flush()


def suppress_library_output(func):
    """
    Decorador para suprimir salidas de librerías problemáticas.
    
    Uso:
    @suppress_library_output
    def my_function():
        # código que usa librerías problemáticas
        pass
    """
    def wrapper(*args, **kwargs):
        with io.StringIO() as buf, redirect_stdout(buf), redirect_stderr(buf):
            result = func(*args, **kwargs)
        return result
    return wrapper


def safe_library_call(func, *args, **kwargs):
    """
    Ejecuta una función suprimiendo su salida.
    
    Uso:
    result = safe_library_call(argostranslate.translate.translate, text, "es", "en")
    """
    with io.StringIO() as buf, redirect_stdout(buf), redirect_stderr(buf):
        return func(*args, **kwargs)


# Configurar automáticamente al importar
configure_logging()
configure_warnings()
configure_environment()

# Exportar funciones útiles
__all__ = [
    'configure_logging',
    'configure_warnings', 
    'configure_environment',
    'clean_console_output',
    'suppress_library_output',
    'safe_library_call'
]
