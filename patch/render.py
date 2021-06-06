import torch


def render_cy_pt(vertices, new_colors, triangles, b, h, w, device):
    vis_colors = torch.ones((1, vertices.shape[-1]), device=device)
    new_image = render_texture_pt(vertices.squeeze(0), new_colors.squeeze(0), triangles, device, b, h, w, 3)
    face_mask = render_texture_pt(vertices.squeeze(0), vis_colors, triangles, device, b, h, w, 1)
    return face_mask, new_image


def render_texture_pt(vertices, colors, triangles, device, b, h, w, c = 3):
    ''' render mesh by z buffer
    Args:
        vertices: 3 x nver
        colors: 3 x nver
        triangles: 3 x ntri
        h: height
        w: width
    '''
    # initial
    # image = torch.zeros((h, w, c))
    # image1 = torch.zeros((h, w, c))
    image2 = torch.zeros((h, w, c), device=device)

    # depth_buffer = torch.zeros([h, w]) - 999999.
    depth_buffer1 = torch.zeros([h, w], device=device) - 999999.
    # depth_buffer2 = torch.zeros([h, w], device=device) - 999999.
    # triangle depth: approximate the depth to the average value of z in each vertex(v0, v1, v2), since the vertices are closed to each other
    tri_depth = (vertices[2, triangles[0, :]] + vertices[2, triangles[1, :]] + vertices[2, triangles[2, :]]) / 3.
    tri_tex = (colors[:, triangles[0, :]] + colors[:, triangles[1, :]] + colors[:, triangles[2, :]]) / 3.

    umin = torch.max(torch.ceil(torch.min(vertices[0, triangles], dim=0)[0]).type(torch.int), torch.tensor(0, dtype=torch.int))
    umax = torch.min(torch.floor(torch.max(vertices[0, triangles], dim=0)[0]).type(torch.int), torch.tensor(w-1, dtype=torch.int))
    vmin = torch.max(torch.ceil(torch.min(vertices[1, triangles], dim=0)[0]).type(torch.int), torch.tensor(0, dtype=torch.int))
    vmax = torch.min(torch.floor(torch.max(vertices[1, triangles], dim=0)[0]).type(torch.int), torch.tensor(h-1, dtype=torch.int))

    mask = (umin <= umax) & (vmin <= vmax)
    bboxes = torch.masked_select(torch.stack([umin, umax, vmin, vmax]), mask).view(4, -1).T
    # points = torch.cartesian_prod(torch.arange(0, h, device=device), torch.arange(0, w, device=device)).unsqueeze(0).repeat(bboxes.shape[0], 1, 1)
    # c1 = (points[:, 0] >= bboxes[:, 0]).type(torch.int)
    # c2 = (points[:, 0] <= bboxes[:, 1]).type(torch.int)
    # c3 = (points[:, 1] >= bboxes[:, 2]).type(torch.int)
    # c4 = (points[:, 1] <= bboxes[:, 3]).type(torch.int)

    # indices = torch.masked_select(torch.stack([umin, umax, vmin, vmax]), mask).view(4, -1)
    # points = torch.cartesian_prod(torch.arange(0, h, device=device), torch.arange(0, w, device=device))
    # old_points = points
    # points = points.unsqueeze(1)
    # points = points.repeat(1, bboxes.shape[0], 1)
    # c2 = (points[:, :, 0] >= bboxes[:, 0]).type(torch.int)
    # c1 = (points[:, :, 0] <= bboxes[:, 1]).type(torch.int)
    # c4 = (points[:, :, 1] >= bboxes[:, 2]).type(torch.int)
    # c3 = (points[:, :, 1] <= bboxes[:, 3]).type(torch.int)
    #
    # mask = c1 + c2 + c3 + c4
    # mask = torch.nonzero((mask == 4).sum(dim=-1)).squeeze()

    # new_triangles = torch.masked_select(triangles, mask).view(3, -1)
    new_tri_depth = torch.masked_select(tri_depth, mask)
    new_tri_tex = torch.masked_select(tri_tex, mask).view(c, -1)

    # depth_buffer2[depth_buffer2] =
    for i in range(bboxes.shape[0]):
        umin = bboxes[i, 0].item()
        umax = bboxes[i, 1].item()
        vmin = bboxes[i, 2].item()
        vmax = bboxes[i, 3].item()
        # uv_vector = torch.cartesian_prod(torch.arange(umin, umax+1, device=device),
        #                                  torch.arange(vmin, vmax+1, device=device))
        condition = (new_tri_depth[i] > depth_buffer1[vmin:vmax+1, umin:umax+1])
        # condition = (new_tri_depth[i] > depth_buffer1[vmin:vmax+1, umin:umax+1]) & \
        #             (arePointsInTri_pt(uv_vector, vertices[:2, new_triangles[:, i]].unsqueeze(0), umax-umin+1, vmax-vmin+1))
        depth_buffer1[vmin:vmax+1, umin:umax+1] = torch.where(condition,
                                                              new_tri_depth[i].repeat(condition.shape),
                                                              depth_buffer1[vmin:vmax+1, umin:umax+1])

        image2[vmin:vmax + 1, umin:umax + 1, :] = torch.where(condition.unsqueeze(-1).repeat(1, 1, c),
                                                              new_tri_tex[:, i].repeat(condition.shape).view(condition.shape[0], condition.shape[1], -1),
                                                              image2[vmin:vmax + 1, umin:umax + 1, :])

    return image2


def arePointsInTri_pt(points, tri_points, u_range, v_range):
    ''' Judge whether the point is in the triangle
    Method:
        http://blackpawn.com/texts/pointinpoly/
    Args:
        point: [u, v] or [x, y]
        tri_points: three vertices(2d points) of a triangle. 2 coords x 3 vertices
    Returns:
        bool: true for in triangle
    '''
    tp = tri_points

    # vectors
    v0 = tp[:, :, 2] - tp[:, :, 0]
    v1 = tp[:, :, 1] - tp[:, :, 0]
    v2 = points - tp[:, :, 0]

    # dot products
    dot00 = torch.matmul(v0, v0.T)
    dot01 = torch.matmul(v0, v1.T)
    dot02 = torch.matmul(v0, v2.T)
    dot11 = torch.matmul(v1, v1.T)
    dot12 = torch.matmul(v1, v2.T)

    # barycentric coordinates
    if dot00*dot11 - dot01*dot01 == 0:
        inverDeno = 0
    else:
        inverDeno = 1/(dot00*dot11 - dot01*dot01)

    u = (dot11*dot02 - dot01*dot12)*inverDeno
    v = (dot00*dot12 - dot01*dot02)*inverDeno

    # check if point in triangle
    cond = (u >= 0) & (v >= 0) & (u + v < 1)
    cond = cond.squeeze(0).view(u_range, v_range).T
    return cond


def isPointInTri_pt(point, tri_points):
    ''' Judge whether the point is in the triangle
    Method:
        http://blackpawn.com/texts/pointinpoly/
    Args:
        point: [u, v] or [x, y]
        tri_points: three vertices(2d points) of a triangle. 2 coords x 3 vertices
    Returns:
        bool: true for in triangle
    '''
    tp = tri_points

    # vectors
    v0 = tp[:, 2] - tp[:, 0]
    v1 = tp[:, 1] - tp[:, 0]
    v2 = point - tp[:, 0]

    # dot products
    dot00 = torch.matmul(v0.T, v0)
    dot01 = torch.matmul(v0.T, v1)
    dot02 = torch.matmul(v0.T, v2)
    dot11 = torch.matmul(v1.T, v1)
    dot12 = torch.matmul(v1.T, v2)

    # barycentric coordinates
    if dot00*dot11 - dot01*dot01 == 0:
        inverDeno = 0
    else:
        inverDeno = 1/(dot00*dot11 - dot01*dot01)

    u = (dot11*dot02 - dot01*dot12)*inverDeno
    v = (dot00*dot12 - dot01*dot02)*inverDeno

    # check if point in triangle
    return (u >= 0) & (v >= 0) & (u + v < 1)