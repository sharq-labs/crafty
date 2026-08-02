from __future__ import annotations

from dataclasses import dataclass
import hashlib
import numpy as np

@dataclass(frozen=True)
class LocalProblem:
    problem_id: str
    family: str
    dimension: int
    instance: int
    lower: np.ndarray
    upper: np.ndarray
    func: object
    final_target: float
    optimum_x: np.ndarray

def _sphere(z):
    z=np.asarray(z,dtype=np.float64); return float(np.sum(z*z))

def _rastrigin(z):
    z=np.asarray(z,dtype=np.float64); n=z.size
    return float(10*n + np.sum(z*z - 10*np.cos(2*np.pi*z)))

def _rosenbrock(z):
    z=np.asarray(z,dtype=np.float64)
    return float(np.sum(100*(z[1:]-z[:-1]**2)**2 + (1-z[:-1])**2))

def _ackley(z):
    z=np.asarray(z,dtype=np.float64); n=z.size
    return float(-20*np.exp(-0.2*np.sqrt(np.sum(z*z)/n)) - np.exp(np.sum(np.cos(2*np.pi*z))/n) + 20 + np.e)

def _stable_seed(family, dimension, instance):
    raw=f'{family}|{dimension}|{instance}'.encode('utf-8')
    return int.from_bytes(hashlib.sha256(raw).digest()[:8],'little')%(2**32)

def _orthogonal_matrix(rng, dimension):
    A=rng.normal(size=(dimension,dimension)); Q,R=np.linalg.qr(A)
    signs=np.sign(np.diag(R)); signs[signs==0]=1.0
    return Q*signs[None,:]

def _make_transformed(base_func,family,dimension,instance,bound,base_optimum):
    rng=np.random.default_rng(_stable_seed(family,dimension,instance))
    shift=rng.uniform(-0.45*bound,0.45*bound,size=dimension)
    if np.linalg.norm(shift)<0.15*bound:
        shift[0]=0.30*bound if instance%2 else -0.30*bound
    rotation=_orthogonal_matrix(rng,dimension)
    base_optimum=np.asarray(base_optimum,dtype=np.float64)
    def func(x):
        x=np.asarray(x,dtype=np.float64)
        z=rotation@(x-shift)+base_optimum
        return base_func(z)
    return func,shift.copy()

def make_local_suite(dimensions=(2,5),instances=(1,)):
    problems=[]
    families=[
      ('sphere',_sphere,5.0,lambda d:np.zeros(d)),
      ('rastrigin',_rastrigin,5.12,lambda d:np.zeros(d)),
      ('rosenbrock',_rosenbrock,3.0,lambda d:np.ones(d)),
      ('ackley',_ackley,5.0,lambda d:np.zeros(d)),
    ]
    for dim in dimensions:
      dim=int(dim)
      for instance in instances:
        instance=int(instance)
        for name,base_func,bound,opt_factory in families:
          func,optimum_x=_make_transformed(base_func,name,dim,instance,float(bound),opt_factory(dim))
          problems.append(LocalProblem(
            problem_id=f'{name}_d{dim}_i{instance}',family=name,dimension=dim,instance=instance,
            lower=np.full(dim,-bound,dtype=np.float64),upper=np.full(dim,bound,dtype=np.float64),
            func=func,final_target=1e-8,optimum_x=optimum_x))
    return problems
