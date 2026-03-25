Set oShell = CreateObject("WScript.Shell")
oShell.CurrentDirectory = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
oShell.Run "pythonw app_gui.pyw", 0, False
