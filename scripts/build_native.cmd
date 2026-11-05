@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
cd /d "%~dp0.."
if not exist runtime mkdir runtime
cl /nologo /O2 /LD /MT /EHsc /std:c++17 /I vendor\openvr native\capture.cpp /Fo:runtime\capture.obj /Fe:runtime\gatofocus_capture.dll /link vendor\openvr\openvr_api.lib d3d11.lib dxgi.lib d3dcompiler.lib
if errorlevel 1 exit /b 1
copy /Y vendor\openvr\openvr_api.dll runtime\openvr_api.dll >nul
