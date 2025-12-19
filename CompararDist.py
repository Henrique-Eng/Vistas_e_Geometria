# file name: ./${DIR_PATH}/${FILE_NAME}
from math import floor

# REFERENCES AND IMPORTS
# BEGIN>>>>>

import clr
import System

# <<< Python Modules >>>
# BEGIN
# Import traceback module from Iron Python
import traceback
import math
import sys  # necessário para sys.path.append do boilerplate
# END

# Import System Libraries
clr.AddReference("System.Core")
from System.Collections.Generic import List as SystemList

# Import System Libraries
import clr
clr.AddReference("System.Core")
from System import Math as SystemMath

# Import Linq
clr.ImportExtensions(System.Linq)

# Import Dynamo Library Nodes - Geometry
clr.AddReference('ProtoGeometry')
from Autodesk.DesignScript import Geometry as DynamoGeometry

# Import Dynamo Library Nodes - Core
import clr
clr.AddReference('DSCoreNodes')
from DSCore import Math as DynamoMath
clr.AddReference('DSCoreNodes')
from DSCore import List as DynamoList

# Import Dynamo Library Nodes - Core
clr.AddReference('DSCoreNodes')
from DSCore import Color as DynamoColor

# Import Dynamo Geometry Color
# https://forum.dynamobim.com/t/geometrycolor-bygeometrycolor-inside-python/52724
clr.AddReference('GeometryColor')
from Modifiers import GeometryColor as DynamoGeometryColorize

# Import Dynamo Library Nodes - Revit
clr.AddReference("RevitNodes")
import Revit as RevitNodes

# Import ToDSType(bool) extension method
clr.ImportExtensions(RevitNodes.Elements)
clr.ImportExtensions(RevitNodes.GeometryConversion)

# Import DocumentManager and TransactionManager
clr.AddReference("RevitServices")
import RevitServices
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

# Import Revit API
clr.AddReference("RevitAPI")
import Autodesk
from Autodesk.Revit.DB import *

# Import Revit User Interface API
clr.AddReference("RevitAPIUI")
from Autodesk.Revit.UI import *

# Import Revit IFC API
# https://forum.dynamobim.com/t/ifcexportutils/4833/7?u=ricardo_freitas
clr.AddReference('RevitAPIIFC')
from Autodesk.Revit.DB.IFC import *

# Import Dynamo Services
clr.AddReference('DynamoServices')
from Dynamo import Events as DynamoEvents

# Active Dynamo Workspace Path
workspaceFullPath = DynamoEvents.ExecutionEvents.ActiveSession.CurrentWorkspacePath
workspacePath = '\\'.join(workspaceFullPath.split('\\')[0:-1])

# REFERENCES AND IMPORTS
# END<<<<<

# FUNCTIONS
# BEGIN>>>>>

# <<< Your classes and functions here >>>
module_dir_path = r"C:\Classes Revit"
sys.path.append(module_dir_path)
try:
    from pydynamo import *
except:
    # mantém execução mesmo se o pacote customizado não existir
    pass

def ensure_list(x):
    """Garante lista."""
    try:
        # objetos DS têm Count? preferimos caminho seguro:
        iter(x)
        if isinstance(x, (str, bytes)):
            return [x]
        return list(x)
    except TypeError:
        return [x]

def get_coord(pt, axis):
    """Retorna coord X/Y/Z do ponto, seja DS Point ou Revit XYZ."""
    ax = str(axis).upper() if axis is not None else "Z"
    if ax == "X":
        return pt.X
    if ax == "Y":
        return pt.Y
    # padrão: Z
    return pt.Z

# FUNCTIONS
# END<<<<<

# INPUTS AND VARIABLES DECLARATIONS
# BEGIN>>>>>

doc = DocumentManager.Instance.CurrentDBDocument
uiapp = DocumentManager.Instance.CurrentUIApplication
app = uiapp.Application
uidoc = DocumentManager.Instance.CurrentUIApplication.ActiveUIDocument

# Entradas do nó
list_points_in = IN[0]          # 1 ponto ou lista de pontos
base_point_in  = IN[1]          # ponto base
axis_in        = IN[2] or "Z"   # "X", "Y" ou "Z"

# Limite opcional (IN[3]); padrão 5.0
threshold = 5.0
try:
    threshold = float(IN[3]) if IN[3] is not None else 5.0
except Exception:
    pass

result = {}

# INPUTS AND VARIABLES DECLARATIONS
# END<<<<<

# MAIN CODE
# BEGIN>>>>>

try:
    errorReport = None

    # start transaction (não vamos modificar o doc, mas mantemos padrão do boilerplate)
    TransactionManager.Instance.EnsureInTransaction(doc)

    pts = ensure_list(list_points_in)
    base_pt = ensure_list(base_point_in)[0]

    # Distância **assinada** ao longo do eixo escolhido:
    deltas = [(get_coord(p, axis_in) - get_coord(base_pt, axis_in)) for p in pts]

    # Índices com |delta| < threshold
    idx_abs_lt_threshold = [i for i, d in enumerate(deltas) if abs(d) < threshold]

    # Monta dicionário de saída (mantém deltas e índices filtrados)
    result = {
        "deltas": deltas,
        "threshold": threshold,
        "indices_abs_lt_threshold": idx_abs_lt_threshold,
        # opcionalmente, os valores também (útil para depurar):
        "values_abs_lt_threshold": [deltas[i] for i in idx_abs_lt_threshold]
    }

    # End transaction
    TransactionManager.Instance.TransactionTaskDone()

except Exception as e:
    # if error occurs anywhere in the process catch it
    errorReport = traceback.format_exc()

# Assign your output to the OUT variable
if errorReport is None:
    OUT = result
else:
    OUT = errorReport
# MAIN CODE
# END<<<<<
