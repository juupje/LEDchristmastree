import numpy as np

def convex_hull(points, edges=False):
    if len(points) < 3:
        return points
    
    def orientation(p, q, r):
        """Returns the orientation of the triplet (p, q, r).
        0: Collinear
        1: Clockwise
        -1: Counterclockwise
        """
        val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
        if val == 0:
            return 0
        return 1 if val > 0 else -1

    # Find the point with the highest y-coordinate
    anchor_idx = np.argmax(points[:,1])
    anchor = points[anchor_idx]

    # Sort the points based on polar angle with respect to the anchor point
    polar_angles = (np.arctan2(points[:,1] - anchor[1], points[:,0] - anchor[0]) + 2 * np.pi) % (2 * np.pi)
    sorted_idx = np.argsort(polar_angles)
    sorted_points = points[sorted_idx]

    # Initialize the convex hull with the anchor point and the first two sorted points
    convex_hull = [anchor, sorted_points[1]]
    indices = [anchor_idx, sorted_idx[1]]
    # Iterate through the sorted points and build the convex hull
    for i in range(2, len(sorted_points)):
        while len(convex_hull) > 1 and orientation(convex_hull[-2], convex_hull[-1], sorted_points[i]) != -1:
            convex_hull.pop()
            indices.pop()
        convex_hull.append(sorted_points[i])
        indices.append(sorted_idx[i])
    bool_indices = np.zeros(points.shape[0], dtype=bool)
    bool_indices[np.array(indices)] = True
    if edges:
        return bool_indices, np.array(convex_hull), np.stack((convex_hull, np.roll(convex_hull,shift=1,axis=0)),axis=1)
    else:
        return bool_indices, np.array(convex_hull)

def find_edges(p, edges):
    #find the two edges that intersect y=p[1]
    target_edges = ~((edges[:,0,1]<=p[1]) ^ (edges[:,1,1]>=p[1]))
    return edges[target_edges]

def construct_line(p1, p2):
    dy = p1[1]-p2[1]
    dx = p1[0]-p2[0]
    c = np.array([-dy, dx])
    b = c.T@p1

    #ensure that points left of the line result in c.T@p<b
    p = np.array([p1[0]-1, p1[1]])
    if(c.T@p<b):
        return c, b
    return -c, -b

def project(points, hull_indices, edges):
    #points = (N_p, 2)
    #edges = (N_e, 2, 2)
    edges_ = np.expand_dims(edges,axis=-1) #(N_e, 2 points, 2 coordinates, 1)
    target_edges = ~((edges_[:,0,1]<=points[:,1]) ^ (edges_[:,1,1]>=points[:,1]))
    #target _edges = (N_e, N_p)
    target_edges = target_edges.T #(N_p, N_e) -> binary array across edges for every point
    
    hull = points[hull_indices]
    left_bound  = np.min(hull[:,0])
    right_bound = np.max(hull[:,0])
    upper_bound = np.max(hull[:,1])
    lower_bound = np.min(hull[:,1])
    width = right_bound-left_bound
    projection = np.empty_like(points)
    middle_line = construct_line(hull[np.argmax(hull[:,1])], hull[np.argmin(hull[:,1])])
    for i in range(points.shape[0]):
        if(hull_indices[i]):
            if(points[i,1]==upper_bound or points[i,1]==lower_bound):
                projection[i] = points[i]
            elif(middle_line[0]@points[i]<middle_line[1]):
                #points is on the left
                projection[i] = [left_bound, points[i,1]]
            else:
                #point is on the right
                projection[i] = [right_bound, points[i,1]]
        else:
            lr_edges = edges[target_edges[i]]
            assert lr_edges.shape[0]==2
            xs = []
            for k in range(2):
                a = (lr_edges[k,1,1]-lr_edges[k,0,1])/(lr_edges[k,1,0]-lr_edges[k,0,0])
                b = lr_edges[k,1,1]-a*lr_edges[k,1,0]
                xs.append((points[i,1]-b)/a)
            d = abs(xs[0]-xs[1])
            x = left_bound+(points[i,0]-min(xs))/d*width
            projection[i] = [x,points[i,1]]
    projection[:,0] = (projection[:,0]-np.min(projection[:,0]))/(np.max(projection[:,0]-np.min(projection[:,0])))*2-1
    projection[:,1] = (projection[:,1]-np.min(projection[:,1]))/(np.max(projection[:,1]-np.min(projection[:,1])))*2-1
    return projection