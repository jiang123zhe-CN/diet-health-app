def calc_tdee(weight_kg: float, height_cm: float, age: int, gender: str) -> int:
    """Mifflin-St Jeor 公式计算基础代谢，乘以活动系数1.55"""
    if gender == "male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    return int(bmr * 1.55)


def calc_macros(tdee: int, weight_kg: float, goal_type: str) -> dict:
    """根据目标计算每日宏量营养素"""
    if goal_type == "fat_loss":
        calories = int(tdee * 0.80)
        protein_g = round(weight_kg * 2.0, 1)
    elif goal_type == "muscle_gain":
        calories = int(tdee * 1.10)
        protein_g = round(weight_kg * 1.8, 1)
    else:
        calories = tdee
        protein_g = round(weight_kg * 1.5, 1)

    fat_g = round(calories * 0.25 / 9, 1)
    carbs_g = round((calories - protein_g * 4 - fat_g * 9) / 4, 1)

    return {
        "calories": calories,
        "protein_g": protein_g,
        "carbs_g": carbs_g,
        "fat_g": fat_g,
    }


def validate_nutrition(meal: dict) -> tuple[bool, str]:
    """营养数据合理性校验"""
    cal = meal.get("calories", 0)
    protein = meal.get("protein_g", 0)
    carbs = meal.get("carbs_g", 0)
    fat = meal.get("fat_g", 0)

    if cal < 100 or cal > 1200:
        return False, f"热量 {cal} 超出合理范围(100-1200)"
    if protein < 0 or protein > 100:
        return False, f"蛋白质 {protein}g 超出合理范围"
    if carbs < 0 or carbs > 150:
        return False, f"碳水 {carbs}g 超出合理范围"

    calc_cal = protein * 4 + carbs * 4 + fat * 9
    if abs(calc_cal - cal) / max(cal, 1) > 0.3:
        return False, f"宏量营养素计算热量({calc_cal:.0f})与声称热量({cal})偏差>30%"

    return True, "ok"
