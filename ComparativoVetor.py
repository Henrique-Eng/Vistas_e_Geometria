# file name: ./${DIR_PATH}/${FILE_NAME}
from math import floor

# REFERENCES AND IMPORTS
# BEGIN>>>>>

import clr
import System
import sys
import traceback
import math

clr.AddReference("System.Core")
from System.Collections.Generic import List as SystemList
from System import Math as SystemMath
clr.ImportExtensions(System.Linq)

# Dynamo Geometry
clr.AddReference('ProtoGeometry')
from Autodesk.DesignScript import Geometry as DynamoGeometry

# DSCore (mantido no boilerplate)
clr.AddReference('DSCoreNodes')
from DSCore import Math as DynamoMath
from DSCore import List as DynamoList
from DSCore import Color as DynamoColor

clr.AddReference('GeometryColor')
from Modifiers import GeometryColor as DynamoGeometryColorize

# Revit / Services (mantidos no boilerplate)
clr.AddReference("RevitNodes")
import Revit as RevitNodes
clr.ImportExtensions(RevitNodes.Elements)
clr.ImportExtensions(RevitNodes.GeometryConversion)

clr.AddReference("RevitServices")
import RevitServices
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

clr.AddReference("RevitAPI")
import Autodesk
from Autodesk.Revit.DB import *

clr.AddReference("RevitAPIUI")
from Autodesk.Revit.UI import *

clr.AddReference('RevitAPIIFC')
from Autodesk.Revit.DB.IFC import *

clr.AddReference('DynamoServices')
from Dynamo import Events as DynamoEvents

workspaceFullPath = DynamoEvents.ExecutionEvents.ActiveSession.CurrentWorkspacePath
workspacePath = '\\'.join(workspaceFullPath.split('\\')[0:-1])

# FUNCTIONS
# BEGIN>>>>>

module_dir_path = r"C:\Classes Revit"
sys.path.append(module_dir_path)
try:
    from pydynamo import *
except:
    pass

def _is_sequence(obj):
    return isinstance(obj, (list, tuple))

def _is_number(x):
    return isinstance(x, (int, float))

def _looks_like_vector(obj):
    return hasattr(obj, 'X') and hasattr(obj, 'Y') and not callable(getattr(obj, 'X')) and not callable(getattr(obj, 'Y'))

def _as_xyz(v):
    """
    Retorna [x,y,z] (DS Vector/Point, Revit XYZ ou lista/tupla).
    Lista com 1 vetor é desempacotada.
    """
    if _looks_like_vector(v):
        return [float(getattr(v,'X')), float(getattr(v,'Y')), float(getattr(v,'Z',0.0))]
    try:
        if isinstance(v, XYZ) or "Autodesk.Revit.DB.XYZ" in str(type(v)):
            return [float(v.X), float(v.Y), float(v.Z)]
    except:
        pass
    if _is_sequence(v):
        if len(v) == 1:
            return _as_xyz(v[0])
        if len(v) >= 2 and all(_is_number(c) for c in v[:min(3,len(v))]):
            return [float(v[0]), float(v[1]), float(v[2] if len(v) > 2 else 0.0)]
        raise TypeError("Recebida lista de vetores; compare por item ou use broadcast.")
    raise TypeError("Tipo de vetor não suportado: {}".format(type(v)))

def _fix_zero(x, eps):
    # normaliza -0.0/0.0 e valores muito próximos de zero
    return 0.0 if (abs(x) <= eps or x == 0.0) else x

def _norm(v):
    return math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])

def _normalize(v, eps):
    n = _norm(v)
    if n <= eps:
        return [0.0, 0.0, 0.0], n
    return [v[0]/n, v[1]/n, v[2]/n], n

def _vec_equal(a, b, tol, ignore_sign=True):
    # cap de tolerância para evitar valores gigantes (ex.: 1.0)
    eps = max(1e-9, min(abs(tol), 1e-3))

    A = [_fix_zero(c, eps) for c in _as_xyz(a)]
    B = [_fix_zero(c, eps) for c in _as_xyz(b)]

    # compara como DIREÇÃO: normaliza e, se pedido, alinha o sinal
    Ahat, na = _normalize(A, eps)
    Bhat, nb = _normalize(B, eps)

    # vetores nulos: se ambos ~0, considere iguais; se só um, diferentes
    if na <= eps and nb <= eps:
        return True
    if na <= eps or nb <= eps:
        return False

    if ignore_sign:
        # se apontam para hemisférios opostos, inverte B
        if (Ahat[0]*Bhat[0] + Ahat[1]*Bhat[1] + Ahat[2]*Bhat[2]) < 0:
            Bhat = [-Bhat[0], -Bhat[1], -Bhat[2]]

    # comparação componente-a-componente (direção alinhada)
    return (abs(Ahat[0] - Bhat[0]) <= eps and
            abs(Ahat[1] - Bhat[1]) <= eps and
            abs(Ahat[2] - Bhat[2]) <= eps)

def _compare_any(a, b, tol, ignore_sign):
    a_is_seq = _is_sequence(a)
    b_is_seq = _is_sequence(b)

    if a_is_seq and b_is_seq:
        if len(a) != len(b):
            m = min(len(a), len(b))
            return [_compare_any(a[i], b[i], tol, ignore_sign) for i in range(m)]
        return [_compare_any(x, y, tol, ignore_sign) for x, y in zip(a, b)]

    if a_is_seq and not b_is_seq:
        if len(a) == 1:
            return _compare_any(a[0], b, tol, ignore_sign)
        return [_compare_any(x, b, tol, ignore_sign) for x in a]

    if b_is_seq and not a_is_seq:
        if len(b) == 1:
            return _compare_any(a, b[0], tol, ignore_sign)
        return [_compare_any(a, y, tol, ignore_sign) for y in b]

    return _vec_equal(a, b, tol, ignore_sign)

# INPUTS E VARS
doc  = DocumentManager.Instance.CurrentDBDocument
uiapp = DocumentManager.Instance.CurrentUIApplication
app  = uiapp.Application
uidoc = uiapp.ActiveUIDocument

A_in = IN[0]
B_in = IN[1]

# tolerância: IN[3] (fallback IN[2], senão 1e-9)
tol = 1e-9
for idx in (3, 2):
    try:
        vtol = IN[idx]
        if vtol is None:
            continue
        if _is_sequence(vtol) and len(vtol) > 0:
            vtol = vtol[0]
        tol = float(vtol)
        break
    except:
        continue

# Ignorar sinal: IN[4] (opcional); padrão True
ignore_sign = True
try:
    flag = IN[4]
    if flag is not None:
        if _is_sequence(flag) and len(flag) > 0:
            flag = flag[0]
        ignore_sign = bool(flag)
except:
    pass

result = None

# MAIN CODE
try:
    errorReport = None
    TransactionManager.Instance.EnsureInTransaction(doc)
    result = _compare_any(A_in, B_in, tol, ignore_sign)
    TransactionManager.Instance.TransactionTaskDone()
except Exception as e:
    errorReport = traceback.format_exc()

OUT = result if errorReport is None else errorReport
# MAIN CODE
# END<<<<<
