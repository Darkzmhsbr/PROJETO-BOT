import base64
import io
from PIL import Image

def decode_base64_to_image(base64_string):
    """
    Converte uma string base64 em uma imagem
    
    Args:
        base64_string: String em formato base64
        
    Returns:
        bytes: Bytes da imagem
    """
    # Remove o prefixo 'data:image/png;base64,' se existir
    if "base64," in base64_string:
        base64_string = base64_string.split("base64,")[1]
    
    try:    
        image_data = base64.b64decode(base64_string)
        return image_data
    except Exception as e:
        print(f"Erro ao decodificar base64: {str(e)}")
        # Retorna uma imagem vazia em caso de erro
        return None

def format_currency(value_in_cents):
    """
    Formata o valor em centavos para o formato de moeda (R$)
    
    Args:
        value_in_cents: Valor em centavos
        
    Returns:
        str: Valor formatado como moeda
    """
    value_in_reais = value_in_cents / 100
    return f"R$ {value_in_reais:.2f}".replace(".", ",")