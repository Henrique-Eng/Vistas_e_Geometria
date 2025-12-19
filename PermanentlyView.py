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
import sys   # <— necessário por causa do sys.path.append no boilerplate

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
from pydynamo import *

def ensure_list(x):
    """Garante lista (flatteando níveis simples)."""
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        # achata um nível
        flat = []
        for i in x:
            if isinstance(i, (list, tuple)):
                flat.extend(list(i))
            else:
                flat.append(i)
        return flat
    return [x]

def to_api_view(v):
    """Converte wrapper do Dynamo para Autodesk.Revit.DB.View."""
    try:
        # Em geral UnwrapElement existe no ambiente do Python Node
        api = UnwrapElement(v)
    except:
        # fallback para propriedades comuns
        api = getattr(v, "InternalElement", v)
    # Confere tipo
    return api if isinstance(api, Autodesk.Revit.DB.View) else None

# FUNCTIONS
# END<<<<<

# INPUTS AND VARIABLES DECLARATIONS
# BEGIN>>>>>

doc = DocumentManager.Instance.CurrentDBDocument
uiapp = DocumentManager.Instance.CurrentUIApplication
app = uiapp.Application
uidoc = DocumentManager.Instance.CurrentUIApplication.ActiveUIDocument

# entrada: views (única ou lista)
views_in = IN[0]

result = []

# INPUTS AND VARIABLES DECLARATIONS
# END<<<<<

# MAIN CODE
# BEGIN>>>>>

try:
    errorReport = None

    # Normaliza entradas
    items = ensure_list(views_in)

    # Converte para API e prepara as saídas alinhadas ao input
    out_views = []
    out_success = []

    # start transaction
    TransactionManager.Instance.EnsureInTransaction(doc)

    # Opcional: filtrar com LINQ (demonstração)
    # Constrói lista tipada e filtra fora de template views
    typed = SystemList[Autodesk.Revit.DB.View]()
    for it in items:
        api_v = to_api_view(it)
        if api_v: typed.Add(api_v)

    # cria coleção filtrada (não obrigatório usar; manteremos correspondência com a entrada)
    non_templates = typed.Where(lambda v: not v.IsTemplate)

    # Percorre na ordem das entradas para manter mapeamento 1:1
    for it in items:
        api_v = to_api_view(it)
        if not api_v:
            out_views.append(None)
            out_success.append(False)
            continue

        # devolvemos sempre o wrapper para o Dynamo
        dyn_v = api_v.ToDSType(True)

        if api_v.IsTemplate:
            # não aplicável em templates
            out_views.append(dyn_v)
            out_success.append(False)
            continue

        # Chama View.ConvertTemporaryHideIsolateToPermanent()
        # Retorna True se alguma ocultação/isolate temporária foi tornada permanente
        try:
            ok = api_v.ConvertTemporaryHideIsolateToPermanent()
        except Exception as ex_call:
            ok = False

        out_views.append(dyn_v)
        out_success.append(bool(ok))

    # opcional, força atualização do documento
    doc.Regenerate()

    # End transaction
    TransactionManager.Instance.TransactionTaskDone()

except Exception as e:
    # if error occurs anywhere in the process catch it
    errorReport = traceback.format_exc()

# Assign your output to the OUT variable
if errorReport is None:
    # Saídas: [views (wrappers), sucesso True/False]
    OUT = [out_views, out_success]
else:
    OUT = errorReport
# MAIN CODE
# END<<<<<
