import google.generativeai as genai
import re
from PIL import Image
import io
import os



# Configurá tu clave API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


# Cargamos la imagen
image_path = "hamburguesa2.jpeg"
with open(image_path, "rb") as f:
    image_data = f.read()

image = Image.open(io.BytesIO(image_data))

# Inicializar el modelo Gemini Pro Vision # This model is deprecated
# model = 0

modelo = genai.GenerativeModel("gemini-2.0-flash")

prompt = """ 

I'm going to send you photos of food dishes. My goal is to obtain a Python dictionary where the first key-value pair is: general food type detected in the image: instances that feature the general food in the image. The following elements are: the key, atomically or individually, food items detected in the image, and the values, the approximate quantities (in grams) of each of the detected foods. I can then query the Edamam API for nutritional information on each of the detected foods. Therefore, the detected foods must exist in the API.

To do this, you must return a Python dictionary that follows these rules:
The first key-value pair in the dictionary is keyed to the type of food: If it's a margherita pizza, return only pizza; if there's a triple burger with fries, return only a burger; if there's ravioli with bolognese, return ravioli; if there's empanadas, return empanada.

The value of this key-value is the number of times that general food item appears in the image: If there are 2 hot dogs, the value is 2. If there is a noodle dish, only 1 is entered; if there is a pizza, 1 is entered, and so on for all the items.
The format is as follows:

food = {"Food General Name": instances that food item appears}

Example with an image showing 3 empanadas:
food = {"Empanada": 3}

Example with an Argentinian Milanese:
food = {"Milanese steak": 1}

Example where a double-meat burger with lettuce, tomato, and other items appears, you just need to enter the generic category:
food = {“hamburger”: 1}

If the food item is detected, such as a hamburger, where the meat, tomato, etc. are visible, then the next elements of the dictionary will follow the following format: “Food on the plate”: instances that food item appears:

food = {“Food General Name”: instances that food item appears, “portion type + food name1”: average_weight_of_a_portion_of_food1, “portion type + food name2”: average_weight_of_a_portion_of_food2}

The weight should be calculated as:
average_weight_of_a_portion × number of times the food item appears in the image
Example:
- If there is a hamburger that has 2 slices of tomato that weigh on average ~20g each, there are 2 buns and 2 hamburger patties weighing ~100g each on average, 2 lettuce leaves weighing ~10g each on average, and 2 slices of cheddar cheese weighing ~20g each on average, then you have to return the following dictionary: 
`food = {“hamburger”:1, "hamburger bun": 200, "hamburger meat": 200, "tomato slice": 40, "lettuce leaf": 20, "cheese": 40}`

Common cases where you should break down food items:
- Pizza: pizza dough, cheese, tomato sauce, pepperoni slices, vegetables, etc.
- Pasta: pasta type (noodles, spaghetti, ravioli, or sorrentino), Bolognese sauce, grated cheese, etc.
- Empanadas: empanada dough, minced meat, onion, hard-boiled egg, olives, etc.

Only returns the dictionary `food = {...}`. If no food item is detected, returns:

food = {}

"""

# Mandar la imagen con un prompt
response = modelo.generate_content(
    [image, prompt]
)

deteccion = response.text

# Mostrar la respuesta
print(deteccion)


# Extraer la parte relevante del texto usando expresiones regulares
match = re.search(r"food\s*=\s*({.*?})", deteccion, re.DOTALL)

if match:
    dict_str = match.group(1)
    
    # Crear un diccionario vacío
    food_dict = {}
    
    # Dividir la cadena en pares clave-valor
    items = dict_str[1:-1].split(",")  # Eliminar las llaves y dividir por comas
    
    for item in items:
        # Dividir cada par clave-valor por dos puntos
        key_value = item.split(":")
        
        # Limpiar la clave y el valor
        key = key_value[0].strip().strip("'\"")  # Eliminar espacios y comillas
        value = key_value[1].strip()
        
        # Convertir el valor a entero si es posible
        try:
            value = int(value)
        except ValueError:
            pass  # Si no es un entero, dejarlo como cadena
        
        # Agregar la clave y el valor al diccionario
        food_dict[key] = value
    
    print(food_dict)
else:
    print("No se encontró el diccionario en el texto.")