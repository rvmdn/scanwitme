Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)

If fso.FileExists(currentDir & "\.venv\Scripts\pythonw.exe") Then
    WshShell.Run """" & currentDir & "\.venv\Scripts\pythonw.exe"" -m scanwitme", 0, False
ElseIf fso.FileExists(currentDir & "\dist\ScanWitMe\ScanWitMe.exe") Then
    WshShell.Run """" & currentDir & "\dist\ScanWitMe\ScanWitMe.exe""", 1, False
Else
    MsgBox "ScanWitMe.exe maupun .venv tidak ditemukan!", vbCritical, "ScanWitMe"
End If
