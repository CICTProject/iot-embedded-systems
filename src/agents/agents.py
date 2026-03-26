def evaluate_energy_state(battery_level):
    if battery_level < 20:
        return "deep_sleep"
    elif battery_level < 50:
        return "idle"
    return "active"