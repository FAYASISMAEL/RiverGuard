def calculate_priority(affected, repeat_count):
    reasons, score = [], 0
    rules = [
        (bool(affected['water_intakes']), 3, 'Water intake detected downstream'),
        (bool(affected['settlements']), 2, 'Settlement detected downstream'),
        (repeat_count > 0, 2, 'Repeated reports on this segment in the last 30 days'),
        (any(a['distance_downstream'] <= 1500 for a in affected['settlements'] + affected['water_intakes']), 2, 'Settlement or water intake within 1.5 km downstream'),
        (bool(affected['monitoring_points']), 1, 'Monitoring station detected downstream'),
    ]
    for applies, points, reason in rules:
        if applies:
            score += points
            reasons.append(f'{reason} (+{points})')
    return dict(score=score, level='CRITICAL' if score >= 10 else 'HIGH' if score >= 7 else 'MEDIUM' if score >= 3 else 'LOW', reasons=reasons or ['No mapped downstream assets within the configured corridor'])
