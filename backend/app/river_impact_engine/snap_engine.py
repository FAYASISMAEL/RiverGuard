from shapely.geometry import Point

class ProximityError(ValueError):
    pass

class SnapEngine:
    def __init__(self, lines, project, inverse, threshold):
        self.lines, self.project, self.inverse, self.threshold = lines, project, inverse, threshold

    def snap(self, latitude, longitude):
        point = Point(*self.project(longitude, latitude))
        segment = min(self.lines, key=lambda key: self.lines[key].distance(point))
        line = self.lines[segment]
        offset = line.project(point)
        snapped = line.interpolate(offset)
        distance = point.distance(snapped)
        if distance > self.threshold:
            raise ProximityError('Selected location is too far from the mapped river. Please choose a location closer to the river.')
        lon, lat = self.inverse(snapped.x, snapped.y)
        return dict(segment_id=segment, latitude=lat, longitude=lon, snap_distance_m=round(distance, 1), offset_m=offset)
