import adsk.core
result = {"documents": [d0.name for d0 in app.documents], "active": app.activeDocument.name if app.activeDocument else None}
