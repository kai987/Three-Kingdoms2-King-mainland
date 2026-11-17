"""Rebuild the native map's sea and reshaped northeast terrain from its coastline."""
from collections import deque


SEA = bytes((0, 42, 248, 255))
LOWER_WEI = bytes((33, 69, 255, 255))
CELL = 2
# Match the original Fujian/Guangdong raster: a short dark rim, a quick blue
# transition and sparse offshore flecks. Distances are native pixels.
COAST_PROFILE = ((0, (0, 3, 3, 255)), (2.8, (0, 3, 8, 255)),
                 (4.5, (0, 5, 26, 255)), (5.4, (0, 13, 111, 255)),
                 (6.7, (0, 42, 213, 255)), (7.8, (3, 58, 241, 255)))


def is_blue(pixel):
    r, g, b = pixel[:3]
    return b >= 86 and b > max(r, g)+45


def neighbors(i, width, size):
    if i % width:
        yield i - 1
    if i % width != width - 1:
        yield i + 1
    if i >= width:
        yield i - width
    if i < size - width:
        yield i + width


def distances(mask, width, radius):
    """Capped distance in pixel-art cells from the nearest marked cell."""
    size = len(mask)
    distance = bytearray(0 if value else radius for value in mask)
    queue = deque(i for i, value in enumerate(mask)
                  if value and any(not mask[j] for j in neighbors(i, width, size)))
    while queue:
        i = queue.popleft()
        step = distance[i] + 1
        if step == radius:
            continue
        for j in neighbors(i, width, size):
            if distance[j] > step:
                distance[j] = step
                queue.append(j)
    return distance


def shore_depth_field(ocean, from_shore, width):
    """Reconstruct a signed shoreline in native pixels from the 2px geography grid."""
    inland = distances(ocean, width, 6)
    depth = [2*sea-1 if in_sea else 1-2*land
             for in_sea, sea, land in zip(ocean, from_shore, inland)]
    height = len(depth)//width
    softened = depth.copy()
    # Round the steps in the old mask near the coast. A small weighted stencil
    # retains narrow channels and the seaward shape of each peninsula.
    for i, value in enumerate(depth):
        if -11 < value < 17:
            x, y = i % width, i // width
            left, right = max(0, x-1), min(width-1, x+1)
            top, bottom = max(0, y-1)*width, min(height-1, y+1)*width
            middle = y*width
            softened[i] = (depth[top+left] + 2*depth[top+x] + depth[top+right]
                           + 2*depth[middle+left] + 4*value + 2*depth[middle+right]
                           + depth[bottom+left] + 2*depth[bottom+x] + depth[bottom+right]) / 16
    return softened


def sample_shore_depth(field, width, x, y):
    """Interpolate at individual native pixel centers rather than whole 2px cells."""
    left, top = (x-1)//CELL, (y-1)//CELL
    right = min(width-1, left+1)
    bottom = min(len(field)//width-1, top+1)
    left, top = max(0, left), max(0, top)
    wx, wy = (1 if x % CELL else 3), (1 if y % CELL else 3)
    a = field[top*width+left]*(4-wx) + field[top*width+right]*wx
    b = field[bottom*width+left]*(4-wx) + field[bottom*width+right]*wx
    return (a*(4-wy) + b*wy) / 16


def ocean_cells(texture, size, shore, crop):
    """Trace open water across the whole world at the same grid as river art."""
    width, height = (length // CELL for length in size)
    stride = size[0] * 4
    candidates = bytearray(width * height)
    left, top, across, down = (crop[key] // CELL for key in ('x', 'y', 'width', 'height'))
    for y in range(height):
        for x in range(width):
            i = y * width + x
            if left <= x < left + across and top <= y < top + down:
                sx, sy = (x-left) * CELL, (y-top) * CELL
                candidates[i] = not shore[(sy * (across * CELL) + sx)*4 + 1]
                continue
            offset = y * CELL * stride + x * CELL * 4
            pixel = texture[offset:offset+4]
            candidates[i] = is_blue(pixel) and pixel not in (SEA, LOWER_WEI)
    # Only water connected to the east or south boundary belongs to the sea.
    seeds = set(range(width*(height-1), width*height)) | set(range(width-1, width*height, width))
    ocean = bytearray(width * height)
    queue = deque(i for i in seeds if candidates[i])
    for i in queue:
        ocean[i] = 1
    while queue:
        i = queue.popleft()
        for j in neighbors(i, width, len(ocean)):
            if candidates[j] and not ocean[j]:
                ocean[j] = 1
                queue.append(j)
    return ocean


def noise(x, y):
    value = (x * 0x1F123BB5 ^ y * 0x5F356495) & 0xffffffff
    value = ((value ^ (value >> 15)) * 0x2C1B3C6D) & 0xffffffff
    return (value ^ (value >> 12)) & 255


def meadow(x, y):
    field, grain = noise(x//2, y//2), noise(x, y)
    if grain < 40 and field < 136:
        return bytes((31, 192 + field//8, 30, 255))
    tint = (field-128)//18 + (grain-128)//32
    return bytes((44 + tint, 230 + tint, 46 + tint, 255))


def sea_color(x, y, distance):
    grain = noise(x+741, y)
    shade = noise(x//7, y//7) // 40
    if distance < 9 and grain < (10 - distance)*9:
        return bytes((1, 15+shade+distance*2, 109+distance*11, 255))
    coast = max(0, 7-distance)
    return bytes((6, 74+shade-coast*4, 251-coast*6, 255))


def mix_color(start, end, weight):
    return bytes(round(a + (b-a)*weight) for a, b in zip(start, end))


def varying_shore_width(x, y):
    cell = 8
    gx, rx = divmod(x, cell)
    gy, ry = divmod(y, cell)
    top = noise(gx+427, gy)*(cell-rx) + noise(gx+428, gy)*rx
    bottom = noise(gx+427, gy+1)*(cell-rx) + noise(gx+428, gy+1)*rx
    return ((top*(cell-ry) + bottom*ry)/(cell*cell) - 128) / 85


def shore_land(x, y, distance, land):
    """Darken only the narrow land-facing bevel of a shore."""
    width = 3 + varying_shore_width(x, y)*.45
    factor = max(0, min(1, distance/width))
    return mix_color((1, 20, 2, 255), land, factor**1.1)


def shore_color(x, y, distance):
    """Shade an individual water pixel with the native shoreline profile."""
    open_water = sea_color(x//CELL, y//CELL, 9)
    depth = max(0, distance + varying_shore_width(x, y)*min(1, distance/4))
    stops = (*COAST_PROFILE, (11, open_water))
    color = open_water
    for (near, near_color), (far, far_color) in zip(stops, stops[1:]):
        if depth < far:
            color = mix_color(near_color, far_color, (depth-near)/(far-near))
            break
    if 7 < distance < 27:
        patch = noise(x//3+198, y//2)
        fleck = patch*.78 + noise(x+741, y)*.22
        if fleck < (27-distance)*4:
            color = mix_color(color, (1, 19, 109, 255), .48+noise(x+91, y//2)/1024)
    return color


def render_world_surface(output, base, hydro, original, size, shore, crop, island_changes):
    """Paint one world surface, with rivers and the existing foreground retained."""
    width, height = size
    left, top, across, down = (crop[key] for key in ('x', 'y', 'width', 'height'))
    if (any(value % CELL for value in (left, top, across, down))
            or not (0 <= left < left + across <= width and 0 <= top < top + down <= height)):
        raise ValueError('Coastline mask must fit the world pixel grid')
    grid_width = width // CELL
    coast_width = across // CELL
    old_land = bytearray()
    new_land = bytearray()
    for y in range(0, down, CELL):
        for x in range(0, across, CELL):
            cell = (y * across + x) * 4
            old_land.append(bool(shore[cell]))
            new_land.append(bool(shore[cell+1]))
    changed = bytes(a != b for a, b in zip(old_land, new_land))
    shift = distances(changed, coast_width, 14)
    former_shore = distances(bytes(not cell for cell in old_land), coast_width, 11)
    ocean = ocean_cells(output, size, shore, crop)
    from_shore = distances(bytes(not cell for cell in ocean), grid_width, 15)
    depth_field = shore_depth_field(ocean, from_shore, grid_width)
    edits = bytearray(width * height)
    for y in range(height):
        sy = y // CELL
        for x in range(width):
            index = y*width + x
            offset = index*4
            before = hydro[offset:offset+4]
            if base[offset:offset+4] != before or before in (SEA, LOWER_WEI):
                continue
            sx = x // CELL
            in_revision = left <= x < left+across and top <= y < top+down
            if in_revision:
                local = ((y-top)//CELL) * coast_width + (x-left)//CELL
            cell = sy * grid_width + sx
            revised = in_revision and shift[local] < 14
            depth = (sample_shore_depth(depth_field, grid_width, x, y)
                     if revised and -7 < depth_field[cell] < 29 else None)
            if ocean[cell] and (depth is None or depth >= .75):
                if (not in_revision or island_changes[index]) and not is_blue(output[offset:offset+3]):
                    continue
                new = shore_color(x, y, depth) if depth is not None else sea_color(sx, sy, from_shore[cell])
            elif in_revision and (new_land[local] or shift[local] < 14):
                original_pixel = original[offset:offset+4]
                # Remove the former cliff and the old tiled fill. Fade into
                # adjoining native slopes, avoiding rectangular cut lines.
                if not new_land[local] or not old_land[local] or is_blue(original_pixel):
                    weight = 12
                else:
                    weight = min(12, max(0, (11-former_shore[local])*2),
                                 max(0, (14-shift[local])*2))
                land = meadow(sx, sy)
                new = bytes((a*(12-weight)+b*weight)//12
                            for a, b in zip(original_pixel, land)) if weight else original_pixel
                if depth is not None:
                    new = shore_land(x, y, -depth, new)
                    if depth > -.75:
                        coverage = min(1, (depth+.75)/1.5)
                        new = mix_color(new, shore_color(x, y, depth), coverage)
            else:
                continue
            if output[offset:offset+4] != new:
                output[offset:offset+4] = new
                edits[index] = 1
    return edits
