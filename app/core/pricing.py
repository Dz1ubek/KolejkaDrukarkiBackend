from app.core.config import settings


def calculate_estimated_price(
    estimated_weight_g: float,
    estimated_time_hours: float,
) -> int:
    """Calculate the estimated print price in grosze (100 grosze = 1 PLN).

    Formula:
      Total = Base Fee + (Weight * Cost/Gram) + (Hours * Cost/Hour)
    """
    base_fee = settings.BASE_PRINT_FEE_GROSZE
    weight_cost = int(round(estimated_weight_g * settings.COST_PER_GRAM_GROSZE))
    time_cost = int(round(estimated_time_hours * settings.COST_PER_HOUR_GROSZE))
    total = base_fee + max(0, weight_cost) + max(0, time_cost)
    return total
