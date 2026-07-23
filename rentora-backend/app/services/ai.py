from typing import Optional

from app.models.room import Room


def calculate_match_score(room: Room, city: Optional[str] = None, budget: Optional[float] = None) -> int:
    score = 70

    if city:
        room_city = room.property.city.lower()
        if room_city == city.lower():
            score += 15
        elif city.lower() in room_city:
            score += 8

    if budget:
        rent = float(room.rent_amount)
        if rent <= budget:
            closeness = 1 - (budget - rent) / budget if budget > 0 else 0
            score += int(15 * min(closeness, 1))
        else:
            over = (rent - budget) / budget
            score -= int(20 * min(over, 1))

    return max(50, min(score, 99))