#!/usr/bin/env python
"""Fiber reconstruction example script.
"""

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------
from __future__ import print_function, division

# Third-party
import numpy as np
import matplotlib.pyplot as plt
import regreg.api as rr

# Local imports
import sphdif
from sphdif import sphquad as sph
reload(sph)  # For interactive development

# Make global some frequently used functions
from numpy import dot
from numpy.linalg import norm

#-----------------------------------------------------------------------------
# Main script
#-----------------------------------------------------------------------------

# Load quadrature
qsph1_37_492DP = np.loadtxt('data/qsph1-37-492DP.dat')
quad_pnts = qsph1_37_492DP[:, :3]
N = 18        # maximum degree of subspace
n_qpnts = 492  # number of points in quadrature

## # Alternative quadrature points
## from dipy.data import get_sphere
## data_file = get_sphere('symmetric362') # 'symmetric642'
## quad_pnts = np.load(data_file)['vertices']
## N = 18
## n_qpnts = len(quad_pnts)

# Sample signal on lower degree quadrature
qsph1_16_132DP = np.loadtxt('data/qsph1-16-132DP.dat')
sample_pnts  = qsph1_16_132DP[:, :3]
n_sample_pnts = 132

# Create reproducing-kernel (sparse representation) matrix
A_new = sph.interp_matrix(quad_pnts, sample_pnts, n_qpnts, n_sample_pnts, N)

# Create signal
print('Creating signal...')
n_fibers = 1                      # number of Gaussian components (max n=3)
b        = 4000                   # s/mm^2
r_angle  = -np.pi/4
signal   =  np.zeros(n_sample_pnts)
for i in range(n_sample_pnts):
    signal[i] = sph.rand_sig(sample_pnts[i, :3].T, b, n_fibers, r_angle)[1]

SNR = []

nRealizations = 1
for kk in range(nRealizations):
    # Make Rician noise
    sigma  = 0.0                          # standard deviation
    noiseR = sigma * np.random.randn(*signal.shape)
    noiseI = sigma * np.random.randn(*signal.shape)
    noise  = noiseR + 1j*noiseI

    SNR.append(10 * np.log10(norm(signal,2)/norm(noise,2)))
    print('Signal to noise ratio: %0.5g' % SNR[kk])

    # Add noise to signal
    rSig = signal + noise
    rSig = abs(rSig)      # only real part is used in MRI

    # Choose regularization parameter
    # lambda > lambda_max -> zero solution
    lambda_max = 2*norm(dot(A_new.T, rSig.T), np.inf)
    lamb = 0.1275*lambda_max

    print('Solving L1 penalized system\n'
          '\n'
          '    ||Ax - b|| + lam |x|_1, subject to x_i >= 0.'
          '\n\n'
          'Here A is reproducing kernel in sparse matrix form.\n'
          'b is the measured signal and x are the coefficents in\n'
          'the sparse represenation.\n\n')

    A = A_new
    b = rSig

    # Set up the problem
    loss = rr.l2normsq.affine(A, -b, coef=1.)
    sparsity = rr.l1norm(n_qpnts, lagrange=lamb)
    constraint = rr.nonnegative(n_qpnts)

    problem = rr.container(loss, sparsity, constraint)

    # Call the solver
    solver = rr.FISTA(problem)
    solver.fit(debug=False)
    nd_coefs_l1 = solver.composite.coefs

    # Cutoff those coefficients that are less than cutoff
    cutoff = nd_coefs_l1.mean() + 2.5*nd_coefs_l1.std(ddof=1)
    nd_coefs_l1_trim = np.where(nd_coefs_l1 > cutoff, nd_coefs_l1, 0)

    # Get indices needed for sorting coefs, in reverse order.
    sortedIndex = nd_coefs_l1_trim.argsort()[::-1]
    # number of significant coefficients
    nSig = (nd_coefs_l1_trim > 0).sum()
    print('Percent compression: %0.5g' % (100*(1.0 - (nSig/(1.0*n_qpnts)))))

    # Used for taking only some of the points---now using the whole sphere
    # Let -1.5 -> 0 and get only the hemisphere with x>0
    cond  = np.where(quad_pnts[sortedIndex[:nSig], 0] >= -1.5)
    indexPos = sortedIndex[cond]
    points   = quad_pnts[indexPos, :3]

    sphdif.io.save('recon_data', points)

    # Sort by x-coordinate in descending order
    #points = sortrows(points,[-1])

    # Unported matlab sources
    """
    # Start clustering algorithm using cosine distance
    nClusters = 4
    ZZ = linkage(points,'single','cosine')
    [h, t, p] = dendrogram(ZZ,nClusters)

    # Check if there's more than one point in cluster if so, take mean.
    p1 = points(t==1,1:3)
    if(sum(t==1)==1)
      mp1 = p1 mp1 = mp1./norm(mp1)
      mw1 = ndCoefsl1(indexPos(t==1))
    elseif(sum(t==1)>1)
      mp1 = mean(p1) mp1 = mp1./norm(mp1)
      mw1 = mean(ndCoefsl1(indexPos(t==1)))
    end

    p2 = points(t==2,1:3)
    if(sum(t==2)==1)
      mp2 = p2 mp2 = mp2./norm(mp2)
      mw2 = ndCoefsl1(indexPos(t==2))
    elseif(sum(t==2)>1)
      mp2 = mean(p2) mp2 = mp2./norm(mp2)
      mw2 = mean(ndCoefsl1(indexPos(t==2)))
    end

    p3 = points(t==3,1:3)
    if(sum(t==3)==1)
      mp3 = p3 mp3 = mp3./norm(mp3)
      mw3 = ndCoefsl1(indexPos(t==3))
    elseif(sum(t==3)>1)
      mp3 = mean(p3) mp3 = mp3./norm(mp3)
      mw3 = mean(ndCoefsl1(indexPos(t==3)))
    end

    p4 = points(t==4,1:3)
    if(sum(t==4)==1)
      mp4 = p4 mp4 = mp4./norm(mp4)
      mw4 = ndCoefsl1(indexPos(t==4))
    elseif(sum(t==4)>1)
      mp4 = mean(p4) mp4 = mp4./norm(mp4)
      mw4 = mean(ndCoefsl1(indexPos(t==4)))
    end

    # Centroids of the four clusters
    mpoints = [mp1 mp2 mp3 mp4]

    # Sorted by decreasing x values
    mpoints = sortrows(mpoints,[-1])

    # Find angle between fiber 1 and pos-x axis -- Should be 0
    a1(kk) = acos(dot(mpoints(1,1:3),[1 0 0]))*180/pi

    if(mpoints(2,2)>0)
      a2(kk) = acos(dot(mpoints(2,1:3),[cos(-rAngle)  sin(-rAngle) 0]))*180/pi
    else
      a2(kk) = acos(dot(mpoints(2,1:3),[cos(-rAngle) -sin(-rAngle) 0]))*180/pi
    end

    # Find anlge between fibers
    ab(kk) = acos(dot(mpoints(1,1:3),mpoints(2,1:3)))*180/pi

    # ratio of mean coefficients --- indication of volume fraction?
    r(kk) = mw1/mw2


# Get statistics
angle1  = mean(a1); std1     = sqrt(var(a1))
angle2  = mean(a2); std2     = sqrt(var(a2))
anglebw = mean(ab); stdbw    = sqrt(var(ab))
ratio   = mean(r);  stdratio = sqrt(var(r))
    """
