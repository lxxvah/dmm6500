; ======================================================================
; DMM6500_Setup.iss —— DMM6500 综合监控台安装包脚本
; ======================================================================
; 编译方式：
;   1. 双击 DMM6500_Setup.iss（用 Inno Setup Compiler 打开）
;   2. 按 F9 或菜单 Build → Compile
;   3. 生成的安装包在 Output\ 目录
;
; 前置条件：
;   · 已经用 PyInstaller 打包出 dist\DMM6500\ 文件夹
;   · 根目录存在 DMM6500_app.ico 图标文件
; ======================================================================

#define MyAppName        "DMM6500 综合监控台"
#define MyAppNameEN      "DMM6500 Monitor"
#define MyAppVersion     "1.0.0"
#define MyAppPublisher   "得鹿梦鱼"
#define MyAppURL         "https://github.com/你的用户名/dmm6500"
#define MyAppExeName     "DMM6500.exe"
#define MyAppId          "{{B5F3D2E1-9A8C-4F5E-B1D3-6C8E7F2A4D90}"

; 打包输出目录（PyInstaller 生成的）
#define BuildDir         "dist\DMM6500"

; 图标路径（相对本 .iss 所在目录）
#define IconFile         "DMM6500_app.ico"

; 输出安装包文件名
#define OutputName       "DMM6500_Setup_v" + MyAppVersion


[Setup]
; ---------- 应用信息 ----------
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; ---------- 默认安装目录 ----------
DefaultDirName={autopf}\{#MyAppNameEN}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; ---------- 输出 ----------
OutputDir=Output
OutputBaseFilename={#OutputName}
SetupIconFile={#IconFile}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

; ---------- 权限（Windows 10+）----------
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; ---------- 兼容性 ----------
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; ---------- 卸载 ----------
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

; ---------- 界面语言 ----------
ShowLanguageDialog=auto

; ---------- 视觉 ----------
WizardSizePercent=110


[Languages]
Name: "chinese"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"


[Tasks]
; 桌面快捷方式
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked


[Files]
; 拷贝整个 dist\DMM6500 文件夹
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs


[Icons]
; 开始菜单
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"

; 桌面快捷方式
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon


[Run]
; 安装完可选择立即启动
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent


[UninstallDelete]
; 卸载时是否删除数据（默认保留，用户数据在 %APPDATA%，不在安装目录）
; Type: filesandordirs; Name: "{app}\data"
; Type: filesandordirs; Name: "{app}\licensing"


[Code]
// ---------- 卸载时询问是否保留用户数据 ----------
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  // 授权文件在 %APPDATA%\dmm6500\ 由用户自行清理
end;