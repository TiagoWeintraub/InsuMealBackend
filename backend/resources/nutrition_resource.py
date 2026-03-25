import logging
from sqlmodel import Session

from models.meal_plate import MealPlate
from models.user import User
from resources.usda_resource import UsdaResource

logger = logging.getLogger(__name__)


class NutritionResource:
    """
    Recurso nutricional principal.
    Mantiene el contrato del flujo existente y usa USDA como proveedor.
    """

    def __init__(self, session: Session, current_user: User = None):
        self.current_user = current_user
        self.session = session
        self.usda_resource = UsdaResource(session, current_user)

    def post_food_by_natural_language(self, food_name: str, grams: float = 100.0):
        return self.usda_resource.get_food_by_name(food_name)

    def orquest(self, food_dic, meal_plate: MealPlate = None):
        return self.usda_resource.orquest(food_dic, meal_plate)
