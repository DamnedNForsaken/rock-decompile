@echo off
setlocal
rem Run from the project root; generated binaries remain under build/.
if not defined ROCK_VCVARS set "ROCK_VCVARS=C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if not exist "%ROCK_VCVARS%" (
  echo Compiler setup not found. Set ROCK_VCVARS to your vcvars64.bat path.
  exit /b 1
)
call "%ROCK_VCVARS%"
if errorlevel 1 exit /b 1
if not exist build\host\debug mkdir build\host\debug
if not exist build\host\release mkdir build\host\release
cl /nologo /Bv /std:c11 /W4 /WX /Od /LD /Iinclude src\rock_state.c src\rock_scheduler.c src\rock_counter.c src\rock_flags.c /Fobuild\host\debug\ /Febuild\host\debug\rock.dll /link /EXPORT:RockState_Init /EXPORT:RockScheduler_ShouldResume /EXPORT:RockThread_RequestReplacement /EXPORT:RockCounter_Tick /EXPORT:RockFlags_Test
if errorlevel 1 exit /b 1
cl /nologo /std:c11 /W4 /WX /O2 /LD /Iinclude src\rock_state.c src\rock_scheduler.c src\rock_counter.c src\rock_flags.c /Fobuild\host\release\ /Febuild\host\release\rock.dll /link /EXPORT:RockState_Init /EXPORT:RockScheduler_ShouldResume /EXPORT:RockThread_RequestReplacement /EXPORT:RockCounter_Tick /EXPORT:RockFlags_Test
exit /b %errorlevel%
