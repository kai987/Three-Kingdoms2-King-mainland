"""Paint a geographic island with a smooth shore and native terrain colors."""
from math import sqrt

from world_surface import CELL, LOWER_WEI, SEA, is_blue, meadow, mix_color, shore_color, shore_land


def signed_distance(x, y, edges):
    inside = False
    nearest = float('inf')
    for x0, y0, dx, dy, length_squared in edges:
        offset_x, offset_y = x - x0, y - y0
        if (y0 > y) != (y0 + dy > y) and offset_x < dx * offset_y / dy:
            inside = not inside
        position = min(1, max(0, (offset_x*dx + offset_y*dy) / length_squared))
        distance = (offset_x - dx*position)**2 + (offset_y - dy*position)**2
        nearest = min(nearest, distance)
    return sqrt(nearest) if inside else -sqrt(nearest)


def mountain_colors(terrain, size, mountains):
    """Extract the shaded slopes from existing terrain, discarding donor grass."""
    width, height = size
    pixels = {}
    for mountain in mountains:
        left, top, source_width, source_height = mountain['source']
        x0, y0, target_width, target_height = mountain['target']
        if not (0 <= left < left+source_width <= width and
                0 <= top < top+source_height <= height and target_width > 0 and target_height > 0):
            raise ValueError('Invalid existing mountain sample or display size')
        for y in range(max(0, y0), min(height, y0+target_height)):
            sy = top + (y-y0)*source_height//target_height
            for x in range(max(0, x0), min(width, x0+target_width)):
                sx = left + (x-x0)*source_width//target_width
                start = (sy*width+sx)*4
                color = terrain[start:start+4]
                margin = min(x-x0+.5, x0+target_width-x-.5, y-y0+.5, y0+target_height-y-.5)
                coverage = min(1, margin/3, (215-color[1])/70)
                if coverage > 0 and not is_blue(color):
                    previous = pixels.get((x, y), meadow(x//CELL, y//CELL))
                    pixels[x, y] = mix_color(previous, color, coverage)
    return pixels


def render_scenic_island(output, base, hydro, terrain, size, spec, surface_changes):
    width, height = size
    outline = spec['outline']
    peaks = mountain_colors(terrain, size, spec['mountains'])
    if len(outline) < 3:
        raise ValueError('Island outline needs at least three points')
    xs, ys = zip(*outline)
    if max(xs) < 0 or min(xs) >= width or max(ys) < 0 or min(ys) >= height:
        raise ValueError('Island outline is outside the visible world')
    edges = []
    for (x0, y0), (x1, y1) in zip(outline, outline[1:] + outline[:1]):
        dx, dy = x1 - x0, y1 - y0
        if dx or dy:
            edges.append((x0, y0, dx, dy, dx*dx + dy*dy))
    # Use the complete outline for distance and coverage, including sections
    # beyond the map. Clip the paint bounds after registering that outline.
    margin = 27
    left, right = max(0, min(xs)-margin), min(width, max(xs)+margin+1)
    top, bottom = max(0, min(ys)-margin), min(height, max(ys)+margin+1)
    painted = []
    for y in range(top, bottom):
        for x in range(left, right):
            distance = signed_distance(x+.5, y+.5, edges)
            if distance <= -margin:
                continue
            index = y*width+x
            offset = index*4
            before = hydro[offset:offset+4]
            if base[offset:offset+4] != before or not is_blue(before) or before in (SEA, LOWER_WEI):
                raise ValueError(f'Island or its shore overlaps existing terrain at {x},{y}')
            grass = peaks.get((x, y), meadow(x//CELL, y//CELL))
            if distance >= 0.5:
                color = shore_land(x, y, distance, grass)
            else:
                coast = shore_color(x, y, max(0, -distance))
                if distance > -0.5:
                    land = shore_land(x, y, distance, grass)
                    color = mix_color(coast, land, distance+.5)
                else:
                    blend = min(1, (margin+distance)/4)
                    color = mix_color(output[offset:offset+4], coast, blend)
            output[offset:offset+4] = color
            surface_changes[index] = color != base[offset:offset+4]
            if distance >= 0:
                painted.append((x, y))
    if not painted:
        raise ValueError('Island outline must cover at least one native pixel')
    xs, ys = zip(*painted)
    return dict(bounds=[min(xs), min(ys), max(xs), max(ys)], land_pixels=len(painted))
