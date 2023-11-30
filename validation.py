#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 15 22:49:13 2022

@author: joep
"""
import numpy as np
import matplotlib.pyplot as plt

delta_phi=45
N_steps = 8

angles = [i*delta_phi for i in range(N_steps)]
locs = np.array([np.load(f"locations_{i*delta_phi}.npy") for i in range(N_steps)])
print(locs.shape)

x = np.sum(locs[:,:,0]==-1,axis=0)
print(x)

locs = np.load("locations.npy")
fig, axes = plt.subplots(2,2)
axes[0][0].hist(locs[:,0], bins=10)
axes[0][1].hist(locs[:,1], bins=10)
axes[1][0].hist(locs[:,2], bins=10)
axes[1][1].hist(np.arctan2(locs[:,1], locs[:,0])+np.pi, bins=10)
axes[0][0].set_xlabel("$x$")
axes[0][1].set_xlabel("$y$")
axes[1][0].set_xlabel("$z$")
axes[1][1].set_xlabel(r"$\phi$")
fig.tight_layout()
fig.savefig("hists.png", dpi=250)