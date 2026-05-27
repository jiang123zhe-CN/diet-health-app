import json
from typing import Optional
from openai import AsyncOpenAI

from app.core.config import settings
from app.services.nutrition import validate_nutrition

_client: Optional[AsyncOpenAI] = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
        )
    return _client


def build_meal_plan_system_prompt(macros: dict, cooking_level: str, likes: list[str],
                                   dislikes: list[str], allergies: list[str],
                                   diet_profile_summary: str = "",
                                   available_ingredients: list[str] = None) -> str:
    profile_section = ""
    if diet_profile_summary:
        profile_section = f"""

## 用户膳食画像（AI营养师分析）
{diet_profile_summary}

请严格依据上述膳食画像调整方案。"""

    ingredient_library = ""
    if available_ingredients:
        ingredient_library = f"""

## 可用食材库（必须从以下食材中选择）
{', '.join(available_ingredients)}

所有食材的 name 字段必须严格使用上述名称，不要使用近义词或自行编造。"""

    return f"""你是一位注册营养师，为中国健身人群设计个性化饮食方案。

## 核心约束
- 每日热量目标: {macros['calories']} 大卡
- 每日蛋白质: {macros['protein_g']}g
- 每日碳水: {macros['carbs_g']}g
- 每日脂肪: {macros['fat_g']}g
- 每日餐次: 早餐、午餐、晚餐
{profile_section}
## 食材限制
- 用户喜欢的食材: {', '.join(likes) if likes else '无特殊偏好'}
- 用户不喜欢的食材（禁止使用）: {', '.join(dislikes) if dislikes else '无'}
- 用户过敏食材（严格禁止）: {', '.join(allergies) if allergies else '无'}
{ingredient_library}
## 餐次要求
- 早餐(cook): 10分钟内可完成，简单快手
- 午餐(ready_to_eat): 商超即食产品，标注产品类型
- 晚餐(cook): 简单健康，25分钟内完成
- 用户烹饪水平: {cooking_level}

## 输出JSON格式
严格输出如下JSON，不要任何额外文字：
```json
{{
  "days": [
    {{
      "day": 1,
      "meals": [
        {{
          "meal_type": "breakfast",
          "meal_source": "cook",
          "meal_name": "餐食名称",
          "ingredients": [{{"name": "食材名", "quantity_g": 用量克}}],
          "calories": 450, "protein_g": 35.0, "carbs_g": 45.0, "fat_g": 12.0,
          "cooking_time_min": 8,
          "instructions": "简要步骤(50字内)"
        }},
        {{
          "meal_type": "lunch",
          "meal_source": "ready_to_eat",
          "meal_name": "即食产品名称（如：罗森鸡胸肉沙拉）",
          "ingredients": [{{"name": "食材名", "quantity_g": 用量克}}],
          "calories": 550, "protein_g": 40.0, "carbs_g": 50.0, "fat_g": 15.0,
          "cooking_time_min": 0,
          "instructions": "商超即食，无需烹饪"
        }},
        {{
          "meal_type": "dinner",
          "meal_source": "cook",
          "meal_name": "餐食名称",
          "ingredients": [{{"name": "食材名", "quantity_g": 用量克}}],
          "calories": 520, "protein_g": 38.0, "carbs_g": 48.0, "fat_g": 14.0,
          "cooking_time_min": 20,
          "instructions": "简要步骤(50字内)"
        }}
      ]
    }}
  ]
}}
```
确保每日总热量在目标±100大卡范围内，蛋白质达标。每餐3-5种食材。"""


def build_swap_prompt(current_ingredient: str, meal_context: dict) -> str:
    return f"""你是营养师。用户想替换当前食材"{current_ingredient}"。

当前餐食信息:
- 餐名: {meal_context.get('meal_name', '')}
- 热量: {meal_context.get('calories', 0)}cal
- 蛋白质: {meal_context.get('protein_g', 0)}g

请给出3个等价替换建议，保持宏量营养浮动在±10%以内，优先使用常见食材。

严格输出如下JSON:
```json
{{
  "alternatives": [
    {{"name": "食材名", "quantity_g": 用量, "calories_diff": 热量变化, "protein_diff_g": 蛋白质变化, "reason": "推荐理由"}},
    {{"name": "食材名", "quantity_g": 用量, "calories_diff": 热量变化, "protein_diff_g": 蛋白质变化, "reason": "推荐理由"}},
    {{"name": "食材名", "quantity_g": 用量, "calories_diff": 热量变化, "protein_diff_g": 蛋白质变化, "reason": "推荐理由"}}
  ]
}}
```"""


def build_questionnaire_analysis_prompt(answers: dict, user_profile: dict) -> str:
    return f"""你是一位注册营养师。分析以下用户饮食问卷，生成结构化膳食画像。

用户基本信息:
- 年龄: {user_profile.get('age')}
- 性别: {user_profile.get('gender')}
- 身高: {user_profile.get('height_cm')} cm
- 体重: {user_profile.get('weight_kg')} kg
- 目标: {user_profile.get('goal_type')}

问卷回答:
{__import__('json').dumps(answers, ensure_ascii=False, indent=2)}

请分析并输出JSON（不要任何额外文字）:
```json
{{
  "profile_summary": "用户饮食画像概述(80字内)",
  "dietary_recommendations": ["具体推荐1", "具体推荐2", "具体推荐3"],
  "restrictions_summary": "饮食限制与忌口总结",
  "suggested_calorie_adjustment": 0
}}
```
suggested_calorie_adjustment 为建议的热量调整值（正数=增加，负数=减少，0=不变），单位为大卡。"""


def build_monthly_report_prompt(records: list[dict], user_profile: dict) -> str:
    return f"""你是营养师，根据用户过去30天的健康记录生成月度报告。

用户信息:
- 目标: {user_profile.get('goal_type', 'healthy')}
- 当前体重: {user_profile.get('weight_kg', 0)}kg

30天健康记录:
{json.dumps(records, ensure_ascii=False, indent=2)}

请以JSON格式输出:
```json
{{
  "summary": "月度总结(100字内)",
  "weight_analysis": "体重变化分析(50字内)",
  "compliance_analysis": "饮食执行率分析(50字内)",
  "suggestions": "下月建议(100字内)",
  "motivation": "鼓励语(30字内)"
}}
```"""


async def call_deepseek(system_prompt: str, user_prompt: str,
                        max_tokens: int = 16000, temperature: float = 0.7) -> str:
    client = get_client()
    response = await client.chat.completions.create(
        model=settings.QWEN_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def extract_json(text: str) -> dict:
    """从LLM返回中提取JSON"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


def parse_meal_plan_response(raw: str, macros: dict) -> list[dict]:
    """解析AI返回的餐食方案并校验"""
    data = extract_json(raw)
    days_data = data.get("days", [])

    all_meals = []
    invalid_count = 0
    for day_data in days_data:
        day_idx = day_data.get("day", 1)
        for meal_data in day_data.get("meals", []):
            ok, msg = validate_nutrition(meal_data)
            if not ok:
                invalid_count += 1
            meal_data["day_index"] = day_idx
            meal_data["_valid"] = ok
            all_meals.append(meal_data)

    if invalid_count > len(all_meals) * 0.3:
        raise ValueError(f"营养校验失败太多({invalid_count}/{len(all_meals)})，需要重新生成")

    return all_meals
