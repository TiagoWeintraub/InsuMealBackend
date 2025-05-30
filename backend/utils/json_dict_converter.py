import json

def json_to_dict(json_string):
    """
    Convierte un JSON a un diccionario de Python.
    """
    try:
        # Convertir JSON a diccionario
        python_dict = json.loads(json_string)
        return python_dict
    except json.JSONDecodeError as e:
        print(f"Error al decodificar el JSON: {e}")
        return None
    except TypeError as e:
        print(f"Error de tipo: {e}")
        return None
    except Exception as e:
        print(f"Error inesperado: {e}")
        return None


def dict_to_json(dic):
    """
    Convierte un diccionario de Python a JSON.
    """
    try:
        # Convertir el diccionario a una cadena JSON
        json_string = json.dumps(dic, indent=4)
        return json_string
    except TypeError as e:
        print(f"Error de tipo: {e}")
        return None
    except Exception as e:
        print(f"Error inesperado: {e}")
        return None


aaa = {
    "meal_plate_id": 1,
    "ingredients": [
        {
            "id": 1,
            "name": "hamburger bun",
            "carbsPerHundredGrams": 50.15,
            "grams": 100.0,
            "carbs": 50.15
        },
        {
            "id": 2,
            "name": "hamburger meat",
            "carbsPerHundredGrams": 0.0,
            "grams": 100.0,
            "carbs": 0.0
        },
        {
            "id": 3,
            "name": "tomato",
            "carbsPerHundredGrams": 3.89,
            "grams": 20.0,
            "carbs": 0.78
        },
        {
            "id": 4,
            "name": "lettuce",
            "carbsPerHundredGrams": 3.29,
            "grams": 10.0,
            "carbs": 0.33
        },
        {
            "id": 5,
            "name": "cheese",
            "carbsPerHundredGrams": 3.09,
            "grams": 20.0,
            "carbs": 0.62
        },
        {
            "id": 6,
            "name": "pickle",
            "carbsPerHundredGrams": 2.41,
            "grams": 10.0,
            "carbs": 0.24
        }
    ]
}