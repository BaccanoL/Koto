' Koto 启动器 (VBScript - 无控制台窗口)
Set objShell = CreateObject("WScript.Shell")
strPath = CreateObject("WScript.Shell").CurrentDirectory
objShell.Run "python launch.py", 0, False
