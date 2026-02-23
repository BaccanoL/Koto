Set WshShell = CreateObject("WScript.Shell")
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

'Check for Virtual Environment Python
If CreateObject("Scripting.FileSystemObject").FileExists(strPath & "\.venv\Scripts\pythonw.exe") Then
    WshShell.Run chr(34) & strPath & "\.venv\Scripts\pythonw.exe" & chr(34) & " " & chr(34) & strPath & "\koto_app.py" & chr(34), 0
Else
    'Fallback to System Python
    WshShell.Run "pythonw " & chr(34) & strPath & "\koto_app.py" & chr(34), 0
End If
