#!/usr/env/python3
# -*- coding: utf-8 -*-
import numpy as np

N_steps = 8

delta_phi = 360//N_steps

angles = [i*delta_phi for i in range(N_steps)]
locs = np.array([np.load(f"locations/locations_{i*delta_phi:d}.npy") for i in range(N_steps)], dtype=np.float32)
print(locs.shape)
""" Removing images with wrong tagging """

""" End removing images """

#locs.shape = (N_steps x N_lights x 2)
N = locs.shape[1]
w,h = 320, 480

output = np.zeros((N, 3))

def find_min(x):
    idx = 0
    m = np.inf
    for i in range(1,len(x)):
        if(x[i] < m and x[i]>=0):
            m = x[i]
            idx = i
    return idx, m

def find_max(x):
    idx = 0
    m = -1
    for i in range(1,len(x)):
        if(x[i] > m and x[i]>=0):
            m = x[i]
            idx = i
    return idx, m

""" Hard coding start """

""" Hard coding end """

zs = np.stack([locs[i,:,0] for i in range(len(locs))]).astype(np.float32)
zs[zs==-1] = np.nan

print("All nan ids:", np.where(np.isnan(zs).all(axis=0))[0])

z = np.nanmean(zs,axis=0)

diff = np.abs(zs-z)
indices_to_check = np.where(np.nansum(diff,axis=0)/N_steps>6)[0]

diff = diff[:, indices_to_check]
diff[np.isnan(diff)] = np.inf
zs2 = zs.copy()
zs2[np.isnan(zs2)] = 0 #these have 0 weight, so they won't be taken into account anyway
z[indices_to_check] = np.average(zs2[:,indices_to_check],axis=0, weights=1/diff**2)

diff = np.nanmean(np.abs(zs-z),axis=0)
z = np.max(z)-z #define z=0 as the lowest led
print("Large z-diff: ", np.where(diff>20)[0])
output[:, 2] = z

#Preprocessing x,y fitting
x = locs[:,:,1]
#normalize x to [-1,1]
x[x==-1] = np.nan
x /= w/2
x -= 1
print(np.nanmin(x), np.nanmax(x))
angles = np.deg2rad(delta_phi*np.arange(N_steps)).reshape((N_steps,1))
M = np.concatenate((np.cos(angles), -np.sin(angles)), axis=1)
res = np.zeros((N))
for i in range(N):
    idx = np.isnan(x[:,i])
    pos, r, _, _ = np.linalg.lstsq(M[~idx,:], x[~idx,i],rcond=None)
    output[i,:2] = pos*w/2
    if(r.shape==(1,)):
        res[i] = r[0]
        
""" Hard coding """

""" End """
        
if(np.any(output==-1)):
    print("Missing values!")

mu = np.mean(output, axis=0)
print(f"Avg x: {mu[0]:.2f}\nAvg y: {mu[1]:.2f}\nAvg z: {mu[2]:.2f}")
np.save("locations.npy", output)
