using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;

[assembly: System.Reflection.AssemblyTitle("Msty CONSENSUS Launcher")]
[assembly: System.Reflection.AssemblyDescription("Starts Msty background services and launches CONSENSUS with duplicate-process protection.")]
[assembly: System.Reflection.AssemblyProduct("Msty CONSENSUS Launcher")]
[assembly: System.Reflection.AssemblyVersion("1.1.3.0")]
[assembly: System.Reflection.AssemblyFileVersion("1.1.3.0")]
[assembly: System.Reflection.AssemblyInformationalVersion("1.1.3")]

namespace MstyConsensusLauncher
{
    internal static class Program
    {
        private const string LauncherVersion = "1.1.3";
        private const string MutexName = @"Global\MstyConsensusLauncher";
        private const string LauncherExePath = @"G:\Tools\MstyConsensusLauncher\MstyConsensusLauncher.exe";
        private const string LauncherWorkingDirectory = @"G:\Tools\MstyConsensusLauncher";
        private const string ConfigPath = @"G:\Tools\MstyConsensusLauncher\launcher.config.json";
        private const string MstyScript = @"G:\Msty\keep-msty-running.ps1";
        private const string ConsensusRoot = @"G:\CONSENSUS_SYSTEM";
        private const string DefaultConsensusExePath = @"G:\CONSENSUS_SYSTEM\dist\CONSENSUS.exe";
        private const string DefaultLogDir = @"G:\Msty\logs";
        private const string LlamaModelsUrl = "http://127.0.0.1:11454/v1/models";
        private const string DefaultMstyApiUrl = "http://127.0.0.1:11964";
        private const string StartupShortcutName = "Msty + CONSENSUS Launcher.lnk";
        private const int OptionalLlamaWaitSeconds = 45;
        private const int SwHide = 0;
        private const int SwMinimize = 6;

        private static LauncherConfig Config = LauncherConfig.CreateDefault();
        private static ConfigLoadResult ConfigState = ConfigLoadResult.Valid(Config, false);

        [DllImport("kernel32.dll")]
        private static extern bool AttachConsole(int dwProcessId);

        [DllImport("kernel32.dll")]
        private static extern bool AllocConsole();

        [DllImport("user32.dll")]
        private static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

        [STAThread]
        private static int Main(string[] args)
        {
            Mutex instanceMutex = null;
            bool mutexHeld = false;
            try
            {
                instanceMutex = new Mutex(false, MutexName);
                try
                {
                    mutexHeld = instanceMutex.WaitOne(0, false);
                }
                catch (AbandonedMutexException)
                {
                    mutexHeld = true;
                }

                if (!mutexHeld)
                {
                    AttachOutputConsole();
                    WriteStatusLine("Another MstyConsensusLauncher instance is already running. Exiting.");
                    LogConfigEvent(DefaultLogDir, "INSTANCE_ALREADY_RUNNING");
                    return 0;
                }

                ConfigState = LoadOrCreateConfig();
                Config = ConfigState.Config;
                if (ConfigState.IsValid)
                {
                    RotateLogs();
                }

                if (HasArg(args, "--self-test"))
                {
                    return RunSelfTest();
                }
                if (HasArg(args, "--status"))
                {
                    return RunStatus(HasArg(args, "--json"));
                }
                if (HasArg(args, "--print-config"))
                {
                    return PrintEffectiveConfig(HasArg(args, "--json"));
                }
                if (HasArg(args, "--install-shortcuts"))
                {
                    return InstallShortcuts();
                }
                if (HasArg(args, "--diagnose-port"))
                {
                    return DiagnosePort();
                }
                if (HasArg(args, "--diagnose-api"))
                {
                    return DiagnoseApi();
                }
                if (!ConfigState.IsValid)
                {
                    AttachOutputConsole();
                    WriteStatusLine("CONFIG_INVALID: " + ConfigState.ErrorMessage);
                    return 1;
                }
                if (HasArg(args, "--open-logs"))
                {
                    return OpenLogs();
                }
                if (HasArg(args, "--tail-log"))
                {
                    return TailLog();
                }
                if (HasArg(args, "--help"))
                {
                    return PrintHelp();
                }

                Directory.CreateDirectory(Config.LogDir);
                Log("Launcher v" + LauncherVersion + " started with args: " + string.Join(" ", args));

                bool dryRun = HasArg(args, "--dry-run");
                bool startupMode = HasArg(args, "--startup");
                bool noDelay = HasArg(args, "--no-delay");
                bool noRecover = HasArg(args, "--no-recover");

                Log("Stage: preflight. StartupMode=" + startupMode + ", DryRun=" + dryRun + ", NoRecover=" + noRecover + ".");

                if (startupMode && !noDelay)
                {
                    int seconds = NextInclusive(Config.StartupDelayMinSeconds, Config.StartupDelayMaxSeconds);
                    Log("Startup mode: waiting " + seconds + " seconds before booting services.");
                    if (!dryRun)
                    {
                        Thread.Sleep(TimeSpan.FromSeconds(seconds));
                    }
                }

                EnsureFile(MstyScript, "Msty background script");
                EnsureFile(Config.ConsensusExePath, "packaged CONSENSUS executable");
                Log("Stage: preflight complete. Required files are present.");

                if (!dryRun)
                {
                    if (!EnsureMstyReady(noRecover))
                    {
                        Log("Launcher finished without launching CONSENSUS because stale Msty recovery is disabled.");
                        return 2;
                    }
                    Log("Stage: CONSENSUS duplicate check and startup.");
                    StartConsensus();
                }
                else
                {
                    Log("Stage: dry-run duplicate inspection.");
                    ApiEndpointSelection dryRunSelection = SelectMstyApiEndpoint(3, false);
                    if (dryRunSelection.SelectedProbe != null)
                    {
                        Log("CONSENSUS_LAUNCH_ENDPOINT " + dryRunSelection.SelectedProbe.ConfiguredApiUrl + " (dry-run)");
                    }
                    Log(
                        "Dry-run state: mstyProcessRunning=" + IsMstyRunning() +
                        ", mstyModelsReady=" + dryRunSelection.IsReady +
                        ", selectedApi=" + (dryRunSelection.SelectedProbe == null ? "NONE" : dryRunSelection.SelectedProbe.ConfiguredApiUrl) +
                        ", modelCount=" + (dryRunSelection.SelectedProbe == null ? 0 : dryRunSelection.SelectedProbe.ModelCount) +
                        ", llama11454Ready=" + TestHttp(LlamaModelsUrl, 3) +
                        ", consensusExeRunning=" + IsConsensusRunning() +
                        ", noRecover=" + noRecover + ".");
                    Log("Dry run complete. Paths are present.");
                }

                Log("Launcher finished.");
                return 0;
            }
            catch (Exception ex)
            {
                TryLogStatus("ERROR: " + ex);
                ShowError("Msty + CONSENSUS launcher failed.\r\n\r\n" + ex.Message + "\r\n\r\nLog: " + CurrentLogPath());
                return 2;
            }
            finally
            {
                if (mutexHeld && instanceMutex != null)
                {
                    try
                    {
                        instanceMutex.ReleaseMutex();
                    }
                    catch
                    {
                    }
                }
                if (instanceMutex != null)
                {
                    instanceMutex.Dispose();
                }
            }
        }

        private static bool EnsureMstyReady(bool noRecover)
        {
            Log("Stage: Msty duplicate check and startup.");
            StartMstyServices();

            Log("Stage: Msty readiness wait.");
            if (WaitForMsty("initial"))
            {
                return true;
            }

            if (!IsMstyRunning())
            {
                throw new TimeoutException("Msty local API did not respond at " + Config.MstyApiUrl + " and no known Msty process is running.");
            }

            return RecoverStaleMsty(noRecover);
        }

        private static void StartMstyServices()
        {
            ApiEndpointSelection selection = SelectMstyApiEndpoint(3, true);
            ApiModelsProbe modelsProbe = selection.SelectedProbe ?? selection.PrimaryProbe;
            bool localReady = selection.IsReady;
            bool llamaReady = TestHttp(LlamaModelsUrl, 3);
            bool mstyRunning = IsMstyRunning();

            Log("Msty duplicate check: processRunning=" + mstyRunning + ", mstyModelsReady=" + localReady + ", modelCount=" + modelsProbe.ModelCount + ", llama11454Ready=" + llamaReady + ".");
            Log("MSTY_WINDOW_MODE " + Config.MstyWindowMode);
            if (mstyRunning || localReady)
            {
                Log("Skipping Msty launch because an existing Msty process or ready API is already present.");
                ApplyMstyWindowMode("existing");
                return;
            }

            Log("Starting Msty background services.");
            ProcessWindowStyle windowStyle = GetConfiguredWindowStyle();
            var psi = new ProcessStartInfo
            {
                FileName = "powershell.exe",
                Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle " + PowerShellWindowStyleArgument() + " -File " + Quote(MstyScript) + " -ForceG -WindowMode " + Config.MstyWindowMode,
                CreateNoWindow = Config.MstyWindowMode.Equals("hidden", StringComparison.OrdinalIgnoreCase),
                UseShellExecute = false,
                WindowStyle = windowStyle,
                WorkingDirectory = Path.GetDirectoryName(MstyScript)
            };
            Process process = Process.Start(psi);
            if (process != null)
            {
                process.Dispose();
            }
            ApplyMstyWindowMode("launch");
            Log("Msty background script started detached. Launcher will not terminate Msty services on exit.");
        }

        private static ProcessWindowStyle GetConfiguredWindowStyle()
        {
            string mode = (Config.MstyWindowMode ?? "hidden").ToLowerInvariant();
            if (mode == "normal")
            {
                return ProcessWindowStyle.Normal;
            }
            if (mode == "hidden")
            {
                return ProcessWindowStyle.Hidden;
            }
            return ProcessWindowStyle.Minimized;
        }

        private static string PowerShellWindowStyleArgument()
        {
            string mode = (Config.MstyWindowMode ?? "hidden").ToLowerInvariant();
            if (mode == "normal")
            {
                return "Normal";
            }
            if (mode == "hidden")
            {
                return "Hidden";
            }
            return "Minimized";
        }

        private static bool IsValidMstyWindowMode(string mode)
        {
            string normalized = (mode ?? "").Trim().ToLowerInvariant();
            return normalized == "normal" || normalized == "minimized" || normalized == "hidden";
        }

        private static void ApplyMstyWindowMode(string phase)
        {
            string mode = (Config.MstyWindowMode ?? "hidden").ToLowerInvariant();
            if (mode == "normal")
            {
                return;
            }

            bool acted = false;
            foreach (Process process in GetKnownMstyProcesses(true))
            {
                using (process)
                {
                    try
                    {
                        process.Refresh();
                        IntPtr handle = process.MainWindowHandle;
                        if (handle == IntPtr.Zero)
                        {
                            continue;
                        }

                        if (mode == "hidden")
                        {
                            ShowWindow(handle, SwHide);
                            Log("MSTY_WINDOW_HIDDEN: phase=" + phase + ", name=" + process.ProcessName + ", pid=" + process.Id + ".");
                        }
                        else
                        {
                            ShowWindow(handle, SwMinimize);
                            Log("MSTY_WINDOW_MINIMIZED: phase=" + phase + ", name=" + process.ProcessName + ", pid=" + process.Id + ".");
                        }
                        acted = true;
                    }
                    catch (Exception ex)
                    {
                        Log("MSTY_WINDOW_HANDLE_NOT_FOUND: phase=" + phase + ", name=" + process.ProcessName + ", pid=" + process.Id + ", error=" + ex.Message);
                    }
                }
            }

            if (!acted)
            {
                Log("MSTY_WINDOW_HANDLE_NOT_FOUND: phase=" + phase + ", mode=" + mode + ".");
            }
        }

        private static bool WaitForMsty(string phase)
        {
            DateTime deadline = DateTime.UtcNow.AddSeconds(Config.StaleRecoveryTimeoutSeconds);
            DateTime? optionalLlamaDeadline = null;
            bool localReady = false;
            bool llamaReady = false;
            Log("Msty readiness wait started. Phase=" + phase + ", timeoutSeconds=" + Config.StaleRecoveryTimeoutSeconds + ".");

            while (DateTime.UtcNow < deadline)
            {
                ApiEndpointSelection selection = SelectMstyApiEndpoint(4, true);
                ApiModelsProbe modelsProbe = selection.SelectedProbe ?? selection.PrimaryProbe;
                localReady = selection.IsReady;
                llamaReady = TestHttp(LlamaModelsUrl, 4);
                if (localReady && llamaReady)
                {
                    Log("Msty models endpoint at " + modelsProbe.ModelsEndpoint + " is ready with " + modelsProbe.ModelCount + " model(s), and llama server at " + LlamaModelsUrl + " is responding.");
                    ApplyMstyWindowMode("ready");
                    return true;
                }
                if (localReady)
                {
                    if (!optionalLlamaDeadline.HasValue)
                    {
                        optionalLlamaDeadline = DateTime.UtcNow.AddSeconds(OptionalLlamaWaitSeconds);
                        Log("Msty models endpoint at " + modelsProbe.ModelsEndpoint + " is ready with " + modelsProbe.ModelCount + " model(s); waiting briefly for optional llama server.");
                    }
                    else if (DateTime.UtcNow >= optionalLlamaDeadline.Value)
                    {
                        Log("Continuing because Msty models endpoint at " + modelsProbe.ModelsEndpoint + " is ready; llama server is optional for consensus launch.");
                        ApplyMstyWindowMode("ready");
                        return true;
                    }
                }
                Thread.Sleep(TimeSpan.FromSeconds(3));
            }

            ApiEndpointSelection finalSelection = SelectMstyApiEndpoint(5, true);
            ApiModelsProbe finalProbe = finalSelection.SelectedProbe ?? finalSelection.PrimaryProbe;
            localReady = finalSelection.IsReady;
            llamaReady = TestHttp(LlamaModelsUrl, 5);
            Log("Msty readiness timeout. Phase=" + phase + ", mstyModelsReady=" + localReady + ", httpStatus=" + finalProbe.HttpStatusText + ", modelCount=" + finalProbe.ModelCount + ", llama11454Ready=" + llamaReady + ".");

            return localReady;
        }

        private static bool RecoverStaleMsty(bool noRecover)
        {
            Log("STALE_MSTY_DETECTED: known Msty process is running but " + Config.MstyApiUrl + " is not ready after " + Config.StaleRecoveryTimeoutSeconds + " seconds.");
            if (noRecover || !Config.EnableStaleRecovery)
            {
                Log("STALE_MSTY_DETECTED: recovery is disabled by " + (noRecover ? "--no-recover" : "config") + "; no processes will be terminated and CONSENSUS will not be launched.");
                return false;
            }

            Log("Stage: stale Msty recovery. Terminating known Msty/MstyClaw processes only.");
            TerminateKnownMstyProcesses();

            int seconds = NextInclusive(Config.StaleRelaunchDelayMinSeconds, Config.StaleRelaunchDelayMaxSeconds);
            Log("Stage: stale Msty recovery. Waiting " + seconds + " seconds before relaunch.");
            Thread.Sleep(TimeSpan.FromSeconds(seconds));

            Log("Stage: stale Msty recovery. Relaunching Msty.");
            StartMstyServices();

            Log("Stage: stale Msty recovery. Waiting again for " + Config.MstyApiUrl + ".");
            if (!WaitForMsty("recovery"))
            {
                throw new TimeoutException("Msty local API did not respond at " + Config.MstyApiUrl + " after stale-process recovery.");
            }

            return true;
        }

        private static void TerminateKnownMstyProcesses()
        {
            foreach (Process process in GetKnownMstyProcesses(true))
            {
                using (process)
                {
                    try
                    {
                        Log("Terminating known Msty process: name=" + process.ProcessName + ", pid=" + process.Id + ".");
                        process.Kill();
                        if (!process.WaitForExit(10000))
                        {
                            Log("Known Msty process did not exit within 10 seconds: name=" + process.ProcessName + ", pid=" + process.Id + ".");
                        }
                        else
                        {
                            Log("Known Msty process terminated: name=" + process.ProcessName + ", pid=" + process.Id + ".");
                        }
                    }
                    catch (Exception ex)
                    {
                        Log("Failed to terminate known Msty process: name=" + process.ProcessName + ", pid=" + process.Id + ", error=" + ex.Message);
                    }
                }
            }
        }

        private static void StartConsensus()
        {
            if (IsConsensusRunning())
            {
                Log("CONSENSUS appears to already be running; not launching another instance.");
                return;
            }

            ApiEndpointSelection selection = SelectMstyApiEndpoint(5, true);
            if (!selection.IsReady || selection.SelectedProbe == null)
            {
                throw new InvalidOperationException("Cannot launch CONSENSUS because no semantically-ready Msty API endpoint is selected.");
            }

            string selectedUrl = selection.SelectedProbe.ConfiguredApiUrl;
            Log("CONSENSUS_LAUNCH_ENDPOINT " + selectedUrl);
            Log("Launching CONSENSUS executable.");
            var psi = new ProcessStartInfo
            {
                FileName = Config.ConsensusExePath,
                WorkingDirectory = ConsensusRoot,
                UseShellExecute = false
            };
            InjectConsensusEnvironment(psi, selectedUrl);
            Process process = Process.Start(psi);
            if (process != null)
            {
                process.Dispose();
            }
            Log("CONSENSUS executable launched detached. Launcher exit will not terminate it.");
        }

        private static void InjectConsensusEnvironment(ProcessStartInfo psi, string selectedUrl)
        {
            if (!Config.EnableConsensusEnvironmentInjection)
            {
                Log("CONSENSUS_ENV_INJECT_DISABLED");
                return;
            }

            Log("CONSENSUS_ENV_INJECT_STARTED");
            NormalizeCurrentProcessPathEnvironment();
            foreach (KeyValuePair<string, string> item in Config.ConsensusEnvironmentVariables)
            {
                string value = (item.Value ?? "").Replace("{selected_msty_api_url}", selectedUrl);
                psi.EnvironmentVariables[item.Key] = value;
                Log("CONSENSUS_ENV_SET " + item.Key + "=" + RedactValueForLog(item.Key, value));
            }
            Log("CONSENSUS_ENV_INJECT_COMPLETE");
        }

        private static void NormalizeCurrentProcessPathEnvironment()
        {
            try
            {
                string path = Environment.GetEnvironmentVariable("Path", EnvironmentVariableTarget.Process);
                string pathUpper = Environment.GetEnvironmentVariable("PATH", EnvironmentVariableTarget.Process);
                if (!string.IsNullOrEmpty(path) && !string.IsNullOrEmpty(pathUpper))
                {
                    Environment.SetEnvironmentVariable("PATH", null, EnvironmentVariableTarget.Process);
                    Log("CONSENSUS_ENV_NORMALIZED duplicate PATH entry removed from launcher process environment.");
                }
            }
            catch (Exception ex)
            {
                Log("CONSENSUS_ENV_NORMALIZE_WARNING " + ex.Message);
            }
        }

        private static bool IsMstyRunning()
        {
            return IsMstyRunning(true);
        }

        private static bool IsMstyRunning(bool logDetections)
        {
            foreach (Process process in GetKnownMstyProcesses(false))
            {
                using (process)
                {
                    if (logDetections)
                    {
                        Log("Detected existing Msty process: " + process.ProcessName + ".");
                    }
                    return true;
                }
            }

            return false;
        }

        private static Process[] GetKnownMstyProcesses(bool logInspectionErrors)
        {
            return Config.KnownMstyProcessNames
                .SelectMany(processName =>
                {
                    try
                    {
                        return Process.GetProcessesByName(processName);
                    }
                    catch (Exception ex)
                    {
                        if (logInspectionErrors)
                        {
                            Log("Could not inspect Msty process name " + processName + ": " + ex.Message);
                        }
                        return new Process[0];
                    }
                })
                .ToArray();
        }

        private static bool IsConsensusRunning()
        {
            return IsConsensusRunning(true);
        }

        private static bool IsConsensusRunning(bool logDetections)
        {
            try
            {
                foreach (Process process in Process.GetProcessesByName("CONSENSUS"))
                {
                    using (process)
                    {
                        try
                        {
                            string path = process.MainModule == null ? "" : process.MainModule.FileName;
                            if (string.Equals(path, Config.ConsensusExePath, StringComparison.OrdinalIgnoreCase))
                            {
                                if (logDetections)
                                {
                                    Log("Detected existing CONSENSUS executable process at " + path + ".");
                                }
                                return true;
                            }
                            if (logDetections)
                            {
                                Log("Ignoring CONSENSUS-named process with different path: " + path + ".");
                            }
                        }
                        catch (Exception ex)
                        {
                            if (logDetections)
                            {
                                Log("Detected CONSENSUS process but could not read its path; skipping launch to avoid duplicate. " + ex.Message);
                            }
                            return true;
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                if (logDetections)
                {
                    Log("Could not inspect CONSENSUS processes: " + ex.Message);
                }
            }

            return false;
        }

        private static int RunSelfTest()
        {
            try
            {
                bool logDirExistsBeforeSelfTest = Directory.Exists(Config.LogDir);
                if (!logDirExistsBeforeSelfTest)
                {
                    Directory.CreateDirectory(Config.LogDir);
                }

                AttachConsole(-1);
                try
                {
                    Console.SetOut(new StreamWriter(Console.OpenStandardOutput()) { AutoFlush = true });
                }
                catch
                {
                    AllocConsole();
                    Console.SetOut(new StreamWriter(Console.OpenStandardOutput()) { AutoFlush = true });
                }

                Log("SELF_TEST: started for launcher v" + LauncherVersion + ".");
                SelfTestPrinter printer = new SelfTestPrinter();

                printer.Pass("Launcher version", "MstyConsensusLauncher v" + LauncherVersion, true);
                printer.Pass("Single instance mutex", "ACQUIRED", true);
                printer.Report(ConfigState.IsValid, "Config file valid", ConfigPath, true);
                bool logRotationConfigValid = ConfigState.IsValid && Config.LogRetentionDays >= 1 && Config.MaxLogFiles >= 1;
                printer.Report(logRotationConfigValid, "Log rotation config valid", Config.LogRetentionDays + "d / max " + Config.MaxLogFiles + " files", true);
                bool windowModeValid = ConfigState.IsValid && IsValidMstyWindowMode(Config.MstyWindowMode);
                printer.Report(windowModeValid, "Msty window mode valid", Config.MstyWindowMode, true);

                bool endpointConfigured = !string.IsNullOrWhiteSpace(Config.MstyApiUrl);
                printer.Report(endpointConfigured, "Msty API endpoint configured", Config.MstyApiUrl, true);

                ApiEndpoint endpoint = ParseApiEndpoint(Config.MstyApiUrl);
                printer.Report(endpoint.IsValid, "Msty API URL parseable", endpoint.IsValid ? endpoint.Host + ":" + endpoint.Port : endpoint.ErrorMessage, true);

                ApiEndpointSelection apiSelection = SelectMstyApiEndpoint(3, false);
                ApiModelsProbe apiProbe = apiSelection.SelectedProbe ?? apiSelection.PrimaryProbe;
                bool apiReady = apiSelection.IsReady;
                printer.Report(apiProbe.HttpReachable, "Msty models endpoint reachable", apiProbe.HttpReachable ? "HTTP status " + apiProbe.HttpStatusText + "." : apiProbe.ErrorMessage, false);
                printer.Report(apiProbe.JsonValid, "Msty models JSON valid", apiProbe.JsonValid ? "JSON parsed." : "JSON did not parse or endpoint was not reachable.", false);
                printer.Report(apiProbe.HasDataArray, "Msty models data array present", apiProbe.HasDataArray ? "data array present." : "data array missing.", false);
                printer.Report(apiProbe.ModelCount > 0, "Msty model count", apiProbe.ModelCount > 0 ? apiProbe.ModelCount + " model(s) detected." : "No models detected.", false);
                printer.Report(apiSelection.SelectedProbe != null, "Selected Msty API endpoint", apiSelection.SelectedProbe == null ? "No ready endpoint selected." : apiSelection.SelectedProbe.ConfiguredApiUrl, false);
                ValidateFallbackUrls(printer);
                ValidateConsensusEnvironment(printer);
                if (endpoint.IsValid)
                {
                    PortListener[] listeners = GetPortListeners(endpoint.Port);
                    printer.Report(!(listeners.Length > 0 && !apiReady), "Msty API port ownership", listeners.Length > 0 ? DescribePortOwners(listeners) : "No listener detected.", false);
                }

                bool mstyRunning = IsMstyRunning();
                printer.Report(mstyRunning, "Known Msty/MstyClaw process running", mstyRunning ? "At least one known process is running." : "No known Msty process detected.", false);

                bool consensusExists = File.Exists(Config.ConsensusExePath);
                printer.Report(consensusExists, "CONSENSUS.exe exists", Config.ConsensusExePath, true);

                bool consensusRunning = IsConsensusRunning();
                printer.Report(!consensusRunning, "CONSENSUS.exe already running", consensusRunning ? "CONSENSUS is already running." : "CONSENSUS is not running.", false);

                printer.Report(logDirExistsBeforeSelfTest, "Log directory exists", Config.LogDir, true);

                string startupShortcut = GetStartupShortcutPath();
                ShortcutInfo startupInfo = ReadShortcut(startupShortcut);
                bool startupOk = startupInfo.IsValid(LauncherExePath, "--startup", LauncherWorkingDirectory);
                printer.Report(startupOk, "Startup shortcut valid", startupInfo.Describe(), true);

                string startMenuShortcut = GetStartMenuShortcutPath();
                ShortcutInfo startMenuInfo = ReadShortcut(startMenuShortcut);
                bool startMenuOk = startMenuInfo.IsValid(LauncherExePath, "", LauncherWorkingDirectory);
                printer.Report(startMenuOk, "Start Menu shortcut valid for pinning", startMenuInfo.Describe(), false);

                string summary = "SELF_TEST_RESULT: pass=" + printer.PassCount + ", warn=" + printer.WarnCount + ", fail=" + printer.FailCount + ".";
                WriteSelfTestLine(summary);
                Log(summary);

                return printer.FailCount == 0 ? 0 : 1;
            }
            catch (Exception ex)
            {
                string message = "SELF_TEST_RESULT: unexpected exception: " + ex;
                try
                {
                    WriteSelfTestLine("FAIL Unexpected exception: " + ex.Message);
                    Log(message);
                }
                catch
                {
                    // Self-test must return 2 for unexpected exceptions even if logging also fails.
                }
                return 2;
            }
        }

        private static int RunStatus(bool json)
        {
            try
            {
                AttachOutputConsole();

                RuntimeStatus status = RuntimeStatus.Collect();
                if (json)
                {
                    WriteStatusLine(status.ToJson());
                }
                else
                {
                    WriteStatusLine("MstyConsensusLauncher " + status.LauncherVersion);
                    WriteStatusLine("Msty API: " + status.MstyApiStatus);
                    WriteStatusLine("Msty API endpoint: " + (status.MstyApiReady ? "READY" : "NOT_READY"));
                    WriteStatusLine("Model count: " + (status.MstyModelCount >= 0 ? status.MstyModelCount.ToString() : "UNKNOWN"));
                    WriteStatusLine("Selected API endpoint: " + status.SelectedMstyApiUrl);
                    WriteStatusLine("Fallback enabled: " + (status.AllowFallbackApi ? "YES" : "NO"));
                    WriteStatusLine("Msty window mode: " + status.MstyWindowMode);
                    WriteStatusLine("CONSENSUS launch endpoint: " + status.ConsensusLaunchEndpoint);
                    WriteStatusLine("Environment injection: " + (status.EnvironmentInjectionEnabled ? "ENABLED" : "DISABLED"));
                    WriteStatusLine("Known Msty process: " + status.MstyProcessStatus);
                    WriteStatusLine("CONSENSUS.exe: " + status.ConsensusStatus);
                    WriteStatusLine("Port listener: " + (status.PortListenerFound ? "FOUND" : "NOT_FOUND"));
                    WriteStatusLine("Port owner: " + status.PortOwner);
                    WriteStatusLine("Startup shortcut: " + status.StartupShortcutStatus);
                    WriteStatusLine("Start Menu shortcut: " + status.StartMenuShortcutStatus);
                    WriteStatusLine("Single instance lock: " + status.SingleInstanceLockStatus);
                    WriteStatusLine("Log retention: " + status.LogRetentionDays + "d / max " + status.MaxLogFiles + " files");
                    WriteStatusLine("Config path: " + status.ConfigPath);
                    WriteStatusLine("Config valid: " + (status.ConfigValid ? "VALID" : "INVALID"));
                    WriteStatusLine("Last log path: " + status.LastLogPath);
                }

                TryLogStatus("STATUS_RESULT: version=" + status.LauncherVersion +
                    ", mstyApi=" + status.MstyApiStatus +
                    ", mstyApiReady=" + status.MstyApiReady +
                    ", modelCount=" + status.MstyModelCount +
                    ", selectedApi=" + status.SelectedMstyApiUrl +
                    ", allowFallbackApi=" + status.AllowFallbackApi +
                    ", mstyWindowMode=" + status.MstyWindowMode +
                    ", consensusLaunchEndpoint=" + status.ConsensusLaunchEndpoint +
                    ", environmentInjectionEnabled=" + status.EnvironmentInjectionEnabled +
                    ", portListenerFound=" + status.PortListenerFound +
                    ", portOwner=" + status.PortOwner +
                    ", mstyProcess=" + status.MstyProcessStatus +
                    ", consensus=" + status.ConsensusStatus +
                    ", startupShortcut=" + status.StartupShortcutStatus +
                    ", startMenuShortcut=" + status.StartMenuShortcutStatus +
                    ", singleInstanceLock=" + status.SingleInstanceLockStatus +
                    ", logRetentionDays=" + status.LogRetentionDays +
                    ", maxLogFiles=" + status.MaxLogFiles +
                    ", configPath=" + status.ConfigPath +
                    ", configValid=" + status.ConfigValid +
                    ", criticalPathsOk=" + status.CriticalPathsOk + ".");

                return status.CriticalPathsOk ? 0 : 1;
            }
            catch (Exception ex)
            {
                try
                {
                    AttachOutputConsole();
                    WriteStatusLine("STATUS_ERROR: " + ex.Message);
                    TryLogStatus("STATUS_ERROR: " + ex);
                }
                catch
                {
                    // Status mode returns 2 for unexpected exceptions even when reporting fails.
                }
                return 2;
            }
        }

        private static int PrintEffectiveConfig(bool json)
        {
            try
            {
                AttachOutputConsole();
                if (!ConfigState.IsValid)
                {
                    WriteStatusLine("CONFIG_INVALID: " + ConfigState.ErrorMessage);
                    return 1;
                }

                if (json)
                {
                    WriteStatusLine(Config.ToJson(true));
                }
                else
                {
                    WriteStatusLine("MstyConsensusLauncher " + LauncherVersion + " effective config");
                    WriteStatusLine("Config path: " + ConfigPath);
                    WriteStatusLine("msty_api_url: " + Config.MstyApiUrl);
                    WriteStatusLine("fallback_msty_api_urls: " + string.Join(", ", Config.FallbackMstyApiUrls ?? new string[0]));
                    WriteStatusLine("allow_fallback_api: " + Config.AllowFallbackApi);
                    WriteStatusLine("consensus_exe_path: " + Config.ConsensusExePath);
                    WriteStatusLine("log_dir: " + Config.LogDir);
                    WriteStatusLine("startup_delay_seconds: " + Config.StartupDelayMinSeconds + "-" + Config.StartupDelayMaxSeconds);
                    WriteStatusLine("stale_recovery_timeout_seconds: " + Config.StaleRecoveryTimeoutSeconds);
                    WriteStatusLine("log_retention: " + Config.LogRetentionDays + "d / max " + Config.MaxLogFiles + " files");
                    WriteStatusLine("enable_consensus_environment_injection: " + Config.EnableConsensusEnvironmentInjection);
                    WriteStatusLine("consensus_environment_variables:");
                    foreach (KeyValuePair<string, string> item in Config.ConsensusEnvironmentVariables)
                    {
                        WriteStatusLine("  " + item.Key + "=" + RedactValueForLog(item.Key, item.Value));
                    }
                }

                TryLogStatus("PRINT_CONFIG: printed effective config.");
                return 0;
            }
            catch (Exception ex)
            {
                try
                {
                    AttachOutputConsole();
                    WriteStatusLine("PRINT_CONFIG_ERROR: " + ex.Message);
                    TryLogStatus("PRINT_CONFIG_ERROR: " + ex);
                }
                catch
                {
                    // Print-config returns 2 for unexpected exceptions even when reporting fails.
                }
                return 2;
            }
        }

        private static void ValidateFallbackUrls(SelfTestPrinter printer)
        {
            string[] urls = Config.FallbackMstyApiUrls ?? new string[0];
            if (urls.Length == 0)
            {
                printer.Pass("Fallback API URLs", "No fallback URLs configured.", false);
                return;
            }

            foreach (string url in urls)
            {
                ApiEndpoint endpoint = ParseApiEndpoint(url);
                bool critical = Config.AllowFallbackApi;
                printer.Report(endpoint.IsValid, "Fallback API URL valid", endpoint.IsValid ? url : url + " - " + endpoint.ErrorMessage, critical);
            }
        }

        private static void ValidateConsensusEnvironment(SelfTestPrinter printer)
        {
            if (Config.ConsensusEnvironmentVariables == null || Config.ConsensusEnvironmentVariables.Count == 0)
            {
                printer.Report(false, "CONSENSUS environment variables configured", "No environment variables configured.", false);
                return;
            }

            foreach (KeyValuePair<string, string> item in Config.ConsensusEnvironmentVariables)
            {
                bool valid = !string.IsNullOrWhiteSpace(item.Key) && item.Value != null;
                printer.Report(valid, "CONSENSUS environment variable valid", valid ? item.Key + "=" + item.Value : "Invalid environment variable entry.", true);
            }
        }

        private static int DiagnosePort()
        {
            try
            {
                AttachOutputConsole();
                Directory.CreateDirectory(Config.LogDir);
                Log("PORT_DIAGNOSTIC_STARTED");

                if (!ConfigState.IsValid)
                {
                    WriteStatusLine("CONFIG_INVALID: " + ConfigState.ErrorMessage);
                    Log("PORT_DIAGNOSTIC_CONFIG_INVALID: " + ConfigState.ErrorMessage);
                    return 1;
                }

                ApiEndpoint endpoint = ParseApiEndpoint(Config.MstyApiUrl);
                if (!endpoint.IsValid)
                {
                    WriteStatusLine("Invalid configured API URL: " + endpoint.ErrorMessage);
                    Log("PORT_DIAGNOSTIC_INVALID_URL: " + endpoint.ErrorMessage);
                    return 1;
                }

                ApiModelsProbe apiProbe = ProbeMstyModels(3);
                bool apiReady = apiProbe.IsReady;
                PortListener[] listeners = GetPortListeners(endpoint.Port);

                WriteStatusLine("Configured API URL: " + endpoint.Url);
                WriteStatusLine("Parsed host: " + endpoint.Host);
                WriteStatusLine("Parsed port: " + endpoint.Port);
                WriteStatusLine("API readiness: " + (apiReady ? "READY" : "NOT_READY"));
                WriteStatusLine("Port listener: " + (listeners.Length > 0 ? "FOUND" : "NOT_FOUND"));

                if (listeners.Length == 0)
                {
                    WriteStatusLine("Listener PID: NONE");
                    WriteStatusLine("Listener process name: NONE");
                    WriteStatusLine("Listener executable path: UNKNOWN");
                    Log("PORT_NOT_LISTENING: " + endpoint.Port);
                }
                else
                {
                    foreach (PortListener listener in listeners)
                    {
                        WriteStatusLine("Listener PID: " + listener.Pid);
                        WriteStatusLine("Listener process name: " + listener.ProcessName);
                        WriteStatusLine("Listener executable path: " + listener.ExecutablePath);
                    }

                    if (!apiReady)
                    {
                        Log("PORT_OCCUPIED_API_NOT_READY: port=" + endpoint.Port + ", owners=" + DescribePortOwners(listeners));
                    }
                }

                Log("PORT_DIAGNOSTIC_COMPLETE: apiReady=" + apiReady + ", listeners=" + listeners.Length + ".");
                return 0;
            }
            catch (Exception ex)
            {
                try
                {
                    AttachOutputConsole();
                    WriteStatusLine("PORT_DIAGNOSTIC_ERROR: " + ex.Message);
                    TryLogStatus("PORT_DIAGNOSTIC_ERROR: " + ex);
                }
                catch
                {
                    // Diagnose-port returns 2 for unexpected exceptions even if reporting also fails.
                }
                return 2;
            }
        }

        private static int DiagnoseApi()
        {
            try
            {
                AttachOutputConsole();
                Directory.CreateDirectory(Config.LogDir);
                Log("API_DIAGNOSTIC_STARTED");

                if (!ConfigState.IsValid)
                {
                    WriteStatusLine("CONFIG_INVALID: " + ConfigState.ErrorMessage);
                    Log("API_DIAGNOSTIC_CONFIG_INVALID: " + ConfigState.ErrorMessage);
                    Log("API_DIAGNOSTIC_COMPLETE");
                    return 1;
                }

                ApiEndpointSelection selection = SelectMstyApiEndpoint(5, true);
                LogApiProbeResult(selection.PrimaryProbe);
                foreach (ApiModelsProbe fallbackProbe in selection.FallbackProbes)
                {
                    LogApiProbeResult(fallbackProbe);
                }
                WriteStatusLine("Fallback enabled: " + (Config.AllowFallbackApi ? "YES" : "NO"));
                WriteProbeDetails("Primary endpoint", selection.PrimaryProbe);
                foreach (ApiModelsProbe fallbackProbe in selection.FallbackProbes)
                {
                    WriteProbeDetails("Fallback endpoint", fallbackProbe);
                }
                WriteStatusLine("Selected endpoint: " + (selection.SelectedProbe == null ? "NONE" : selection.SelectedProbe.ConfiguredApiUrl));
                Log("API_DIAGNOSTIC_COMPLETE");
                return selection.IsReady ? 0 : 1;
            }
            catch (Exception ex)
            {
                try
                {
                    AttachOutputConsole();
                    WriteStatusLine("API_DIAGNOSTIC_ERROR: " + ex.Message);
                    TryLogStatus("API_DIAGNOSTIC_ERROR: " + ex);
                }
                catch
                {
                    // Diagnose-api returns 2 for unexpected exceptions even if reporting also fails.
                }
                return 2;
            }
        }

        private static void LogApiProbeResult(ApiModelsProbe probe)
        {
            if (probe == null)
            {
                return;
            }
            if (probe.IsReady)
            {
                Log("API_MODELS_READY count=" + probe.ModelCount);
            }
            else if (probe.HttpReachable && probe.HttpStatus != 200)
            {
                Log("API_HTTP_ERROR status=" + probe.HttpStatus);
            }
            else if (probe.HttpReachable && !probe.JsonValid)
            {
                Log("API_JSON_INVALID");
            }
            else if (probe.HttpReachable && probe.ModelCount == 0)
            {
                Log("API_MODELS_EMPTY");
            }
            else if (!probe.HttpReachable)
            {
                Log("API_HTTP_ERROR status=" + probe.HttpStatusText);
            }
        }

        private static void WriteProbeDetails(string label, ApiModelsProbe probe)
        {
            WriteStatusLine(label + ": " + probe.ConfiguredApiUrl);
            WriteStatusLine("  Models endpoint URL: " + probe.ModelsEndpoint);
            WriteStatusLine("  HTTP status: " + probe.HttpStatusText);
            WriteStatusLine("  API readiness: " + (probe.IsReady ? "READY" : "NOT_READY"));
            WriteStatusLine("  JSON valid: " + (probe.JsonValid ? "YES" : "NO"));
            WriteStatusLine("  Model count: " + probe.ModelCount);
            WriteStatusLine("  Model IDs:");
            if (probe.ModelIds.Length == 0)
            {
                WriteStatusLine("    NONE");
                return;
            }

            foreach (string modelId in probe.ModelIds)
            {
                WriteStatusLine("    " + modelId);
            }
        }

        private static int InstallShortcuts()
        {
            try
            {
                Directory.CreateDirectory(Config.LogDir);
                Log("SHORTCUT_INSTALL_STARTED");

                bool startupOk = EnsureShortcut(
                    GetStartupShortcutPath(),
                    LauncherExePath,
                    "--startup",
                    LauncherWorkingDirectory);

                bool startMenuOk = EnsureShortcut(
                    GetStartMenuShortcutPath(),
                    LauncherExePath,
                    "",
                    LauncherWorkingDirectory);

                Log("SHORTCUT_INSTALL_COMPLETE");
                return startupOk && startMenuOk ? 0 : 1;
            }
            catch (Exception ex)
            {
                try
                {
                    AttachOutputConsole();
                    WriteStatusLine("SHORTCUT_INSTALL_ERROR: " + ex.Message);
                    TryLogStatus("SHORTCUT_INSTALL_ERROR: " + ex);
                }
                catch
                {
                    // Install-shortcuts returns 2 for unexpected exceptions even if reporting also fails.
                }
                return 2;
            }
        }

        private static bool EnsureShortcut(string shortcutPath, string targetPath, string arguments, string workingDirectory)
        {
            try
            {
                ShortcutInfo existing = ReadShortcut(shortcutPath);
                bool existed = existing.Exists;
                if (existing.IsValid(targetPath, arguments, workingDirectory))
                {
                    Log("SHORTCUT_ALREADY_VALID " + shortcutPath);
                    return true;
                }

                Directory.CreateDirectory(Path.GetDirectoryName(shortcutPath));
                if (File.Exists(shortcutPath))
                {
                    File.Delete(shortcutPath);
                }
                WriteShortcut(shortcutPath, targetPath, arguments, workingDirectory);
                ShortcutInfo repaired = ReadShortcut(shortcutPath);
                if (!repaired.IsValid(targetPath, arguments, workingDirectory))
                {
                    Log("SHORTCUT_INSTALL_FAILED " + shortcutPath + " - repaired shortcut is invalid: " + repaired.Describe());
                    return false;
                }
                Log((existed ? "SHORTCUT_REPAIRED " : "SHORTCUT_CREATED ") + shortcutPath);
                return true;
            }
            catch (Exception ex)
            {
                Log("SHORTCUT_INSTALL_FAILED " + shortcutPath + " - " + ex.Message);
                return false;
            }
        }

        private static void WriteShortcut(string shortcutPath, string targetPath, string arguments, string workingDirectory)
        {
            Type shellType = Type.GetTypeFromProgID("WScript.Shell");
            if (shellType == null)
            {
                throw new InvalidOperationException("WScript.Shell is unavailable.");
            }

            object shell = Activator.CreateInstance(shellType);
            object shortcut = shellType.InvokeMember("CreateShortcut", BindingFlags.InvokeMethod, null, shell, new object[] { shortcutPath });
            Type shortcutType = shortcut.GetType();
            shortcutType.InvokeMember("TargetPath", BindingFlags.SetProperty, null, shortcut, new object[] { targetPath });
            shortcutType.InvokeMember("Arguments", BindingFlags.SetProperty, null, shortcut, new object[] { arguments });
            shortcutType.InvokeMember("WorkingDirectory", BindingFlags.SetProperty, null, shortcut, new object[] { workingDirectory });
            shortcutType.InvokeMember("IconLocation", BindingFlags.SetProperty, null, shortcut, new object[] { targetPath + ",0" });
            shortcutType.InvokeMember("Description", BindingFlags.SetProperty, null, shortcut, new object[] { "Start Msty background services and launch CONSENSUS" });
            shortcutType.InvokeMember("Save", BindingFlags.InvokeMethod, null, shortcut, null);
        }

        private static int OpenLogs()
        {
            try
            {
                Directory.CreateDirectory(Config.LogDir);
                Log("OPEN_LOGS: opening " + Config.LogDir + ".");
                var psi = new ProcessStartInfo
                {
                    FileName = "explorer.exe",
                    Arguments = Quote(Config.LogDir),
                    UseShellExecute = true
                };
                Process process = Process.Start(psi);
                if (process != null)
                {
                    process.Dispose();
                }
                return 0;
            }
            catch (Exception ex)
            {
                try
                {
                    AttachOutputConsole();
                    WriteStatusLine("OPEN_LOGS_ERROR: " + ex.Message);
                    TryLogStatus("OPEN_LOGS_ERROR: " + ex);
                }
                catch
                {
                    // Open-logs returns failure even if reporting also fails.
                }
                return 2;
            }
        }

        private static int TailLog()
        {
            try
            {
                AttachOutputConsole();
                string latestLog = GetLatestLauncherLogPath();
                if (string.IsNullOrEmpty(latestLog))
                {
                    WriteStatusLine("No launcher logs found in " + Config.LogDir + ".");
                    TryLogStatus("TAIL_LOG: no launcher logs found.");
                    return 1;
                }

                WriteStatusLine("Latest launcher log: " + latestLog);
                foreach (string line in ReadLastLines(latestLog, 80))
                {
                    WriteStatusLine(line);
                }
                TryLogStatus("TAIL_LOG: printed last 80 lines from " + latestLog + ".");
                return 0;
            }
            catch (Exception ex)
            {
                try
                {
                    AttachOutputConsole();
                    WriteStatusLine("TAIL_LOG_ERROR: " + ex.Message);
                    TryLogStatus("TAIL_LOG_ERROR: " + ex);
                }
                catch
                {
                    // Tail-log returns 2 for unexpected exceptions even if reporting also fails.
                }
                return 2;
            }
        }

        private static int PrintHelp()
        {
            try
            {
                AttachOutputConsole();
                WriteStatusLine("MstyConsensusLauncher " + LauncherVersion);
                WriteStatusLine("Supported flags:");
                WriteStatusLine("  --startup");
                WriteStatusLine("  --no-recover");
                WriteStatusLine("  --self-test");
                WriteStatusLine("  --status");
                WriteStatusLine("  --status --json");
                WriteStatusLine("  --print-config");
                WriteStatusLine("  --print-config --json");
                WriteStatusLine("  --install-shortcuts");
                WriteStatusLine("  --diagnose-port");
                WriteStatusLine("  --diagnose-api");
                WriteStatusLine("  --open-logs");
                WriteStatusLine("  --tail-log");
                WriteStatusLine("  --help");
                WriteStatusLine("When enabled, the selected Msty API endpoint is injected into the launched CONSENSUS process environment.");
                TryLogStatus("HELP: printed supported flags.");
                return 0;
            }
            catch (Exception ex)
            {
                try
                {
                    TryLogStatus("HELP_ERROR: " + ex);
                }
                catch
                {
                    // Help returns 2 for unexpected exceptions even if reporting also fails.
                }
                return 2;
            }
        }

        private static void AttachOutputConsole()
        {
            AttachConsole(-1);
            try
            {
                Console.SetOut(new StreamWriter(Console.OpenStandardOutput()) { AutoFlush = true });
            }
            catch
            {
                AllocConsole();
                Console.SetOut(new StreamWriter(Console.OpenStandardOutput()) { AutoFlush = true });
            }
        }

        private static void WriteSelfTestLine(string message)
        {
            Console.WriteLine(message);
            Log("SELF_TEST: " + message);
        }

        private static void WriteStatusLine(string message)
        {
            Console.WriteLine(message);
        }

        private static string GetLatestLauncherLogPath()
        {
            if (!Directory.Exists(Config.LogDir))
            {
                return "";
            }

            FileInfo latest = new DirectoryInfo(Config.LogDir)
                .GetFiles("msty-consensus-launcher-*.log")
                .OrderByDescending(file => file.LastWriteTimeUtc)
                .FirstOrDefault();

            return latest == null ? "" : latest.FullName;
        }

        private static string[] ReadLastLines(string path, int lineCount)
        {
            return File.ReadLines(path)
                .Reverse()
                .Take(lineCount)
                .Reverse()
                .ToArray();
        }

        private static ShortcutInfo ReadShortcut(string shortcutPath)
        {
            if (!File.Exists(shortcutPath))
            {
                return new ShortcutInfo(shortcutPath, false, "", "", "");
            }

            try
            {
                Type shellType = Type.GetTypeFromProgID("WScript.Shell");
                if (shellType == null)
                {
                    return new ShortcutInfo(shortcutPath, true, "", "", "WScript.Shell is unavailable.");
                }

                object shell = Activator.CreateInstance(shellType);
                object shortcut = shellType.InvokeMember("CreateShortcut", BindingFlags.InvokeMethod, null, shell, new object[] { shortcutPath });
                Type shortcutType = shortcut.GetType();
                string targetPath = Convert.ToString(shortcutType.InvokeMember("TargetPath", BindingFlags.GetProperty, null, shortcut, null));
                string arguments = Convert.ToString(shortcutType.InvokeMember("Arguments", BindingFlags.GetProperty, null, shortcut, null));
                string workingDirectory = Convert.ToString(shortcutType.InvokeMember("WorkingDirectory", BindingFlags.GetProperty, null, shortcut, null));
                return new ShortcutInfo(shortcutPath, true, targetPath, arguments, workingDirectory);
            }
            catch (Exception ex)
            {
                return new ShortcutInfo(shortcutPath, true, "", "", "Could not read shortcut metadata: " + ex.Message);
            }
        }

        private static string GetStartupShortcutPath()
        {
            return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Startup), StartupShortcutName);
        }

        private static string GetStartMenuShortcutPath()
        {
            return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs), StartupShortcutName);
        }

        private static string GetShortcutStatus(ShortcutInfo shortcut, string expectedTargetPath, string expectedArguments, string expectedWorkingDirectory)
        {
            if (!shortcut.Exists)
            {
                return "MISSING";
            }

            return shortcut.IsValid(expectedTargetPath, expectedArguments, expectedWorkingDirectory) ? "VALID" : "INVALID";
        }

        private static ApiEndpoint ParseApiEndpoint(string url)
        {
            Uri uri;
            if (string.IsNullOrWhiteSpace(url))
            {
                return ApiEndpoint.Invalid(url, "msty_api_url is empty.");
            }
            if (!Uri.TryCreate(url, UriKind.Absolute, out uri))
            {
                return ApiEndpoint.Invalid(url, "msty_api_url is not an absolute URL.");
            }
            if (string.IsNullOrWhiteSpace(uri.Host))
            {
                return ApiEndpoint.Invalid(url, "msty_api_url host is empty.");
            }
            if (uri.Port <= 0 || uri.Port > 65535)
            {
                return ApiEndpoint.Invalid(url, "msty_api_url port is invalid.");
            }

            return ApiEndpoint.Valid(url, uri.Host, uri.Port);
        }

        private static PortListener[] GetPortListeners(int port)
        {
            if (port <= 0 || port > 65535)
            {
                return new PortListener[0];
            }

            var listeners = new List<PortListener>();
            var seen = new HashSet<int>();
            var psi = new ProcessStartInfo
            {
                FileName = "netstat.exe",
                Arguments = "-ano -p tcp",
                CreateNoWindow = true,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };

            using (Process process = Process.Start(psi))
            {
                if (process == null)
                {
                    return new PortListener[0];
                }

                string output = process.StandardOutput.ReadToEnd();
                process.WaitForExit(10000);
                foreach (string rawLine in output.Split(new[] { "\r\n", "\n" }, StringSplitOptions.RemoveEmptyEntries))
                {
                    string line = rawLine.Trim();
                    if (line.Length == 0 || line.IndexOf("LISTENING", StringComparison.OrdinalIgnoreCase) < 0)
                    {
                        continue;
                    }

                    string[] parts = line.Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
                    if (parts.Length < 5 || !string.Equals(parts[0], "TCP", StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }

                    int localPort;
                    if (!TryParseEndpointPort(parts[1], out localPort) || localPort != port)
                    {
                        continue;
                    }

                    int pid;
                    if (!int.TryParse(parts[parts.Length - 1], out pid) || pid <= 0)
                    {
                        continue;
                    }
                    if (!seen.Add(pid))
                    {
                        continue;
                    }

                    listeners.Add(PortListener.FromPid(pid, parts[1]));
                }
            }

            return listeners.ToArray();
        }

        private static bool TryParseEndpointPort(string endpoint, out int port)
        {
            port = 0;
            if (string.IsNullOrWhiteSpace(endpoint))
            {
                return false;
            }

            string value = endpoint.Trim();
            int index = value.LastIndexOf(':');
            if (index < 0 || index == value.Length - 1)
            {
                return false;
            }

            string portText = value.Substring(index + 1).Trim();
            return int.TryParse(portText, out port);
        }

        private static string DescribePortOwners(PortListener[] listeners)
        {
            if (listeners == null || listeners.Length == 0)
            {
                return "NONE";
            }

            return string.Join(", ", listeners.Select(listener => listener.ProcessName + "(" + listener.Pid + ")").ToArray());
        }

        private static string JsonStringArray(IEnumerable<string> values)
        {
            if (values == null)
            {
                return "[]";
            }

            return "[" + string.Join(",", values.Select(value => "\"" + EscapeJson(value) + "\"").ToArray()) + "]";
        }

        private static string JsonIntArray(IEnumerable<int> values)
        {
            if (values == null)
            {
                return "[]";
            }

            return "[" + string.Join(",", values.Select(value => value.ToString()).ToArray()) + "]";
        }

        private static string JsonProbeResults(IEnumerable<ApiModelsProbe> probes)
        {
            if (probes == null)
            {
                return "[]";
            }

            return "[" + string.Join(",", probes.Select(probe =>
                "{" +
                "\"api_url\":\"" + EscapeJson(probe.ConfiguredApiUrl) + "\"," +
                "\"models_endpoint\":\"" + EscapeJson(probe.ModelsEndpoint) + "\"," +
                "\"http_status\":\"" + EscapeJson(probe.HttpStatusText) + "\"," +
                "\"ready\":" + (probe.IsReady ? "true" : "false") + "," +
                "\"json_valid\":" + (probe.JsonValid ? "true" : "false") + "," +
                "\"model_count\":" + probe.ModelCount + "," +
                "\"model_ids\":" + JsonStringArray(probe.ModelIds) +
                "}").ToArray()) + "]";
        }

        private static string JsonStringDictionary(IDictionary<string, string> values)
        {
            return JsonStringDictionary(values, false);
        }

        private static string JsonStringDictionary(IDictionary<string, string> values, bool redact)
        {
            if (values == null)
            {
                return "{}";
            }

            return "{" + string.Join(",", values.Select(item =>
                "\"" + EscapeJson(item.Key) + "\":\"" + EscapeJson(redact ? RedactValueForLog(item.Key, item.Value) : item.Value) + "\"").ToArray()) + "}";
        }

        private static string RedactValueForLog(string name, string value)
        {
            if (IsSensitiveName(name))
            {
                return "[REDACTED]";
            }

            return value ?? "";
        }

        private static bool IsSensitiveName(string name)
        {
            if (string.IsNullOrWhiteSpace(name))
            {
                return false;
            }

            string normalized = name.ToUpperInvariant();
            return normalized.Contains("TOKEN") ||
                normalized.Contains("SECRET") ||
                normalized.Contains("PASSWORD") ||
                normalized.Contains("PASS") ||
                normalized.Contains("KEY") ||
                normalized.Contains("CREDENTIAL");
        }

        private static string EscapeJson(string value)
        {
            if (value == null)
            {
                return "";
            }

            return value
                .Replace("\\", "\\\\")
                .Replace("\"", "\\\"")
                .Replace("\r", "\\r")
                .Replace("\n", "\\n")
                .Replace("\t", "\\t");
        }

        private static ApiModelsProbe ProbeMstyModels(int timeoutSeconds)
        {
            return ProbeMstyModels(Config.MstyApiUrl, timeoutSeconds);
        }

        private static ApiEndpointSelection SelectMstyApiEndpoint(int timeoutSeconds, bool logSelection)
        {
            ApiModelsProbe primary = ProbeMstyModels(Config.MstyApiUrl, timeoutSeconds);
            var fallbacks = new List<ApiModelsProbe>();
            ApiModelsProbe selected = primary.IsReady ? primary : null;

            if (primary.IsReady)
            {
                if (logSelection)
                {
                    Log("API_SELECTED " + primary.ConfiguredApiUrl);
                }
            }
            else
            {
                if (logSelection)
                {
                    Log("API_PRIMARY_NOT_READY " + Config.MstyApiUrl);
                }

                if (Config.AllowFallbackApi)
                {
                    foreach (string fallbackUrl in Config.FallbackMstyApiUrls ?? new string[0])
                    {
                        if (logSelection)
                        {
                            Log("API_FALLBACK_PROBE " + fallbackUrl);
                        }

                        ApiModelsProbe fallbackProbe = ProbeMstyModels(fallbackUrl, timeoutSeconds);
                        fallbacks.Add(fallbackProbe);
                        if (fallbackProbe.IsReady)
                        {
                            selected = fallbackProbe;
                            if (logSelection)
                            {
                                Log("API_FALLBACK_READY " + fallbackProbe.ConfiguredApiUrl + " count=" + fallbackProbe.ModelCount);
                                Log("API_SELECTED " + fallbackProbe.ConfiguredApiUrl);
                            }
                            break;
                        }
                    }
                }

                if (selected == null && logSelection)
                {
                    Log("API_NO_ENDPOINT_READY");
                }
            }

            return new ApiEndpointSelection
            {
                PrimaryProbe = primary,
                FallbackProbes = fallbacks.ToArray(),
                SelectedProbe = selected
            };
        }

        private static ApiModelsProbe ProbeMstyModels(string apiUrl, int timeoutSeconds)
        {
            string endpoint = BuildModelsEndpoint(apiUrl);
            var probe = new ApiModelsProbe
            {
                ConfiguredApiUrl = apiUrl,
                ModelsEndpoint = endpoint,
                HttpStatus = 0,
                HttpStatusText = "NO_RESPONSE",
                HttpReachable = false,
                JsonValid = false,
                HasDataArray = false,
                ModelIds = new string[0],
                ModelCount = 0,
                ErrorMessage = ""
            };

            try
            {
                var request = (HttpWebRequest)WebRequest.Create(endpoint);
                request.Method = "GET";
                request.Timeout = timeoutSeconds * 1000;
                request.ReadWriteTimeout = timeoutSeconds * 1000;
                using (var response = (HttpWebResponse)request.GetResponse())
                using (var reader = new StreamReader(response.GetResponseStream()))
                {
                    probe.HttpStatus = (int)response.StatusCode;
                    probe.HttpStatusText = ((int)response.StatusCode).ToString();
                    probe.HttpReachable = true;
                    string body = reader.ReadToEnd();
                    ParseModelsJson(probe, body);
                }
            }
            catch (WebException ex)
            {
                HttpWebResponse response = ex.Response as HttpWebResponse;
                if (response != null)
                {
                    using (response)
                    using (var reader = new StreamReader(response.GetResponseStream()))
                    {
                        probe.HttpStatus = (int)response.StatusCode;
                        probe.HttpStatusText = ((int)response.StatusCode).ToString();
                        probe.HttpReachable = true;
                        string body = reader.ReadToEnd();
                        ParseModelsJson(probe, body);
                    }
                }
                else
                {
                    probe.ErrorMessage = ex.Message;
                }
            }
            catch (Exception ex)
            {
                probe.ErrorMessage = ex.Message;
            }

            return probe;
        }

        private static void ParseModelsJson(ApiModelsProbe probe, string body)
        {
            try
            {
                object parsed = new JavaScriptSerializer().DeserializeObject(body ?? "");
                Dictionary<string, object> root = parsed as Dictionary<string, object>;
                if (root == null)
                {
                    probe.JsonValid = true;
                    probe.HasDataArray = false;
                    return;
                }

                probe.JsonValid = true;
                object data;
                if (!root.TryGetValue("data", out data))
                {
                    probe.HasDataArray = false;
                    return;
                }

                object[] items = data as object[];
                if (items == null)
                {
                    probe.HasDataArray = false;
                    return;
                }

                probe.HasDataArray = true;
                var ids = new List<string>();
                foreach (object item in items)
                {
                    Dictionary<string, object> model = item as Dictionary<string, object>;
                    if (model == null)
                    {
                        continue;
                    }

                    object idValue;
                    if (model.TryGetValue("id", out idValue) && idValue != null)
                    {
                        string id = Convert.ToString(idValue);
                        if (!string.IsNullOrWhiteSpace(id))
                        {
                            ids.Add(id);
                        }
                    }
                }

                probe.ModelIds = ids.ToArray();
                probe.ModelCount = items.Length;
            }
            catch (Exception ex)
            {
                probe.JsonValid = false;
                probe.HasDataArray = false;
                probe.ModelIds = new string[0];
                probe.ModelCount = 0;
                probe.ErrorMessage = ex.Message;
            }
        }

        private static string BuildModelsEndpoint(string baseUrl)
        {
            if (string.IsNullOrWhiteSpace(baseUrl))
            {
                return "/v1/models";
            }

            return baseUrl.TrimEnd('/') + "/v1/models";
        }

        private static bool TestHttp(string url, int timeoutSeconds)
        {
            try
            {
                var request = (HttpWebRequest)WebRequest.Create(url);
                request.Method = "GET";
                request.Timeout = timeoutSeconds * 1000;
                request.ReadWriteTimeout = timeoutSeconds * 1000;
                using (var response = (HttpWebResponse)request.GetResponse())
                {
                    return ((int)response.StatusCode >= 200 && (int)response.StatusCode < 500);
                }
            }
            catch
            {
                return false;
            }
        }

        private static void EnsureFile(string path, string label)
        {
            if (!File.Exists(path))
            {
                throw new FileNotFoundException("Missing " + label + ": " + path, path);
            }
        }

        private static bool HasArg(string[] args, string value)
        {
            return args.Any(arg => string.Equals(arg, value, StringComparison.OrdinalIgnoreCase));
        }

        private static string Quote(string value)
        {
            return "\"" + value.Replace("\"", "\\\"") + "\"";
        }

        private static string CurrentLogPath()
        {
            return Path.Combine(Config.LogDir, "msty-consensus-launcher-" + DateTime.Now.ToString("yyyyMMdd") + ".log");
        }

        private static void Log(string message)
        {
            string line = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + " " + message + Environment.NewLine;
            File.AppendAllText(CurrentLogPath(), line);
        }

        private static void TryLogStatus(string message)
        {
            try
            {
                if (Directory.Exists(Config.LogDir))
                {
                    Log(message);
                }
            }
            catch
            {
                // Status output must remain available even if the log cannot be written.
            }
        }

        private static void ShowError(string message)
        {
            try
            {
                System.Windows.Forms.MessageBox.Show(
                    message,
                    "Msty + CONSENSUS Launcher",
                    System.Windows.Forms.MessageBoxButtons.OK,
                    System.Windows.Forms.MessageBoxIcon.Error);
            }
            catch
            {
                // If Windows Forms cannot show a dialog, the log still contains the failure.
            }
        }

        private static void RotateLogs()
        {
            Directory.CreateDirectory(Config.LogDir);
            Log("LOG_ROTATION_STARTED");

            FileInfo[] logs = new DirectoryInfo(Config.LogDir)
                .GetFiles("msty-consensus-launcher-*.log")
                .OrderByDescending(file => file.LastWriteTimeUtc)
                .ToArray();

            DateTime cutoff = DateTime.UtcNow.AddDays(-Config.LogRetentionDays);
            foreach (FileInfo logFile in logs.Where(file => file.LastWriteTimeUtc < cutoff).ToArray())
            {
                TryDeleteLauncherLog(logFile.FullName);
            }

            FileInfo[] remainingLogs = new DirectoryInfo(Config.LogDir)
                .GetFiles("msty-consensus-launcher-*.log")
                .OrderByDescending(file => file.LastWriteTimeUtc)
                .ToArray();

            foreach (FileInfo logFile in remainingLogs.Skip(Config.MaxLogFiles))
            {
                TryDeleteLauncherLog(logFile.FullName);
            }

            Log("LOG_ROTATION_COMPLETE");
        }

        private static void TryDeleteLauncherLog(string path)
        {
            try
            {
                File.Delete(path);
                Log("LOG_ROTATION_DELETED " + path);
            }
            catch (Exception ex)
            {
                Log("LOG_ROTATION_DELETE_FAILED " + path + " - " + ex.Message);
            }
        }

        private static ConfigLoadResult LoadOrCreateConfig()
        {
            LauncherConfig defaults = LauncherConfig.CreateDefault();
            try
            {
                if (!File.Exists(ConfigPath))
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(ConfigPath));
                    File.WriteAllText(ConfigPath, defaults.ToJson(), Encoding.UTF8);
                    LogConfigEvent(defaults.LogDir, "CONFIG_CREATED: " + ConfigPath);
                    return ConfigLoadResult.Valid(defaults, true);
                }

                string json = File.ReadAllText(ConfigPath, Encoding.UTF8);
                object parsed = new JavaScriptSerializer().DeserializeObject(json);
                Dictionary<string, object> values = parsed as Dictionary<string, object>;
                if (values == null)
                {
                    throw new FormatException("Config root must be a JSON object.");
                }

                var defaultsUsed = new List<string>();
                LauncherConfig config = LauncherConfig.CreateDefault();
                config.Version = ReadInt(values, "version", defaults.Version, defaultsUsed);
                config.MstyApiUrl = ReadString(values, "msty_api_url", defaults.MstyApiUrl, defaultsUsed);
                config.ConsensusExePath = ReadString(values, "consensus_exe_path", defaults.ConsensusExePath, defaultsUsed);
                config.LogDir = ReadString(values, "log_dir", defaults.LogDir, defaultsUsed);
                config.StartupDelayMinSeconds = ReadInt(values, "startup_delay_min_seconds", defaults.StartupDelayMinSeconds, defaultsUsed);
                config.StartupDelayMaxSeconds = ReadInt(values, "startup_delay_max_seconds", defaults.StartupDelayMaxSeconds, defaultsUsed);
                config.StaleRecoveryTimeoutSeconds = ReadInt(values, "stale_recovery_timeout_seconds", defaults.StaleRecoveryTimeoutSeconds, defaultsUsed);
                config.StaleRelaunchDelayMinSeconds = ReadInt(values, "stale_relaunch_delay_min_seconds", defaults.StaleRelaunchDelayMinSeconds, defaultsUsed);
                config.StaleRelaunchDelayMaxSeconds = ReadInt(values, "stale_relaunch_delay_max_seconds", defaults.StaleRelaunchDelayMaxSeconds, defaultsUsed);
                config.MstyWindowMode = ReadString(values, "msty_window_mode", defaults.MstyWindowMode, defaultsUsed);
                config.KnownMstyProcessNames = ReadStringArray(values, "known_msty_process_names", defaults.KnownMstyProcessNames, defaultsUsed);
                config.EnableStaleRecovery = ReadBool(values, "enable_stale_recovery", defaults.EnableStaleRecovery, defaultsUsed);
                config.LogRetentionDays = ReadInt(values, "log_retention_days", defaults.LogRetentionDays, defaultsUsed);
                config.MaxLogFiles = ReadInt(values, "max_log_files", defaults.MaxLogFiles, defaultsUsed);
                config.FallbackMstyApiUrls = ReadOptionalStringArray(values, "fallback_msty_api_urls", defaults.FallbackMstyApiUrls, defaultsUsed);
                config.AllowFallbackApi = ReadBool(values, "allow_fallback_api", defaults.AllowFallbackApi, defaultsUsed);
                config.ConsensusEnvironmentVariables = ReadStringDictionary(values, "consensus_environment_variables", defaults.ConsensusEnvironmentVariables, defaultsUsed);
                config.EnableConsensusEnvironmentInjection = ReadBool(values, "enable_consensus_environment_injection", defaults.EnableConsensusEnvironmentInjection, defaultsUsed);
                config.Normalize();

                LogConfigEvent(config.LogDir, "CONFIG_LOADED: " + ConfigPath);
                foreach (string field in defaultsUsed)
                {
                    LogConfigEvent(config.LogDir, "CONFIG_DEFAULT_USED: " + field);
                }

                return ConfigLoadResult.Valid(config, false);
            }
            catch (Exception ex)
            {
                LogConfigEvent(defaults.LogDir, "CONFIG_INVALID: " + ConfigPath + " - " + ex.Message);
                return ConfigLoadResult.Invalid(defaults, ex.Message);
            }
        }

        private static int ReadInt(Dictionary<string, object> values, string key, int defaultValue, List<string> defaultsUsed)
        {
            if (!values.ContainsKey(key))
            {
                defaultsUsed.Add(key);
                return defaultValue;
            }

            return Convert.ToInt32(values[key]);
        }

        private static string ReadString(Dictionary<string, object> values, string key, string defaultValue, List<string> defaultsUsed)
        {
            if (!values.ContainsKey(key))
            {
                defaultsUsed.Add(key);
                return defaultValue;
            }

            string value = Convert.ToString(values[key]);
            if (string.IsNullOrWhiteSpace(value))
            {
                throw new FormatException(key + " must be a non-empty string.");
            }

            return value;
        }

        private static bool ReadBool(Dictionary<string, object> values, string key, bool defaultValue, List<string> defaultsUsed)
        {
            if (!values.ContainsKey(key))
            {
                defaultsUsed.Add(key);
                return defaultValue;
            }

            return Convert.ToBoolean(values[key]);
        }

        private static string[] ReadStringArray(Dictionary<string, object> values, string key, string[] defaultValue, List<string> defaultsUsed)
        {
            if (!values.ContainsKey(key))
            {
                defaultsUsed.Add(key);
                return defaultValue;
            }

            object[] items = values[key] as object[];
            if (items == null)
            {
                throw new FormatException(key + " must be an array of strings.");
            }

            string[] result = items.Select(item => Convert.ToString(item)).Where(item => !string.IsNullOrWhiteSpace(item)).ToArray();
            if (result.Length == 0)
            {
                throw new FormatException(key + " must include at least one process name.");
            }

            return result;
        }

        private static string[] ReadOptionalStringArray(Dictionary<string, object> values, string key, string[] defaultValue, List<string> defaultsUsed)
        {
            if (!values.ContainsKey(key))
            {
                defaultsUsed.Add(key);
                return defaultValue;
            }

            object[] items = values[key] as object[];
            if (items == null)
            {
                throw new FormatException(key + " must be an array of strings.");
            }

            return items.Select(item => Convert.ToString(item)).Where(item => !string.IsNullOrWhiteSpace(item)).ToArray();
        }

        private static Dictionary<string, string> ReadStringDictionary(Dictionary<string, object> values, string key, Dictionary<string, string> defaultValue, List<string> defaultsUsed)
        {
            if (!values.ContainsKey(key))
            {
                defaultsUsed.Add(key);
                return new Dictionary<string, string>(defaultValue, StringComparer.OrdinalIgnoreCase);
            }

            Dictionary<string, object> raw = values[key] as Dictionary<string, object>;
            if (raw == null)
            {
                throw new FormatException(key + " must be an object with string keys and string values.");
            }

            var result = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (KeyValuePair<string, object> item in raw)
            {
                if (string.IsNullOrWhiteSpace(item.Key))
                {
                    throw new FormatException(key + " contains an empty environment variable name.");
                }
                if (!(item.Value is string))
                {
                    throw new FormatException(key + "." + item.Key + " must be a string.");
                }

                result[item.Key] = Convert.ToString(item.Value);
            }

            return result;
        }

        private static int NextInclusive(int min, int max)
        {
            if (max < min)
            {
                int temp = min;
                min = max;
                max = temp;
            }

            return new Random().Next(min, max + 1);
        }

        private static void LogConfigEvent(string logDir, string message)
        {
            try
            {
                Directory.CreateDirectory(logDir);
                string path = Path.Combine(logDir, "msty-consensus-launcher-" + DateTime.Now.ToString("yyyyMMdd") + ".log");
                string line = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + " " + message + Environment.NewLine;
                File.AppendAllText(path, line);
            }
            catch
            {
                // Config load must not crash only because config-event logging failed.
            }
        }

        private sealed class SelfTestPrinter
        {
            public int PassCount { get; private set; }
            public int WarnCount { get; private set; }
            public int FailCount { get; private set; }

            public void Pass(string checkName, string detail, bool critical)
            {
                Write("PASS", checkName, detail);
                PassCount++;
            }

            public void Report(bool passed, string checkName, string detail, bool critical)
            {
                if (passed)
                {
                    Write("PASS", checkName, detail);
                    PassCount++;
                    return;
                }

                if (critical)
                {
                    Write("FAIL", checkName, detail);
                    FailCount++;
                }
                else
                {
                    Write("WARN", checkName, detail);
                    WarnCount++;
                }
            }

            private static void Write(string status, string checkName, string detail)
            {
                WriteSelfTestLine(status + " " + checkName + " - " + detail);
            }
        }

        private sealed class ShortcutInfo
        {
            public ShortcutInfo(string path, bool exists, string targetPath, string arguments, string workingDirectory)
            {
                Path = path;
                Exists = exists;
                TargetPath = targetPath ?? "";
                Arguments = arguments ?? "";
                WorkingDirectory = workingDirectory ?? "";
            }

            public string Path { get; private set; }
            public bool Exists { get; private set; }
            public string TargetPath { get; private set; }
            public string Arguments { get; private set; }
            public string WorkingDirectory { get; private set; }

            public bool IsValid(string expectedTargetPath, string expectedArguments, string expectedWorkingDirectory)
            {
                if (!Exists)
                {
                    return false;
                }
                if (string.IsNullOrWhiteSpace(TargetPath) || string.IsNullOrWhiteSpace(expectedTargetPath))
                {
                    return false;
                }
                if (string.IsNullOrWhiteSpace(WorkingDirectory) || string.IsNullOrWhiteSpace(expectedWorkingDirectory))
                {
                    return false;
                }

                return PathEquals(TargetPath, expectedTargetPath) &&
                    string.Equals((Arguments ?? "").Trim(), (expectedArguments ?? "").Trim(), StringComparison.OrdinalIgnoreCase) &&
                    PathEquals(WorkingDirectory, expectedWorkingDirectory);
            }

            public string Describe()
            {
                if (!Exists)
                {
                    return Path + " does not exist.";
                }

                return "TargetPath=" + TargetPath + "; Arguments=" + Arguments + "; WorkingDirectory=" + WorkingDirectory + ".";
            }

            private static bool PathEquals(string actual, string expected)
            {
                string normalizedActual = NormalizePath(actual);
                string normalizedExpected = NormalizePath(expected);
                return string.Equals(normalizedActual, normalizedExpected, StringComparison.OrdinalIgnoreCase);
            }

            private static string NormalizePath(string value)
            {
                if (string.IsNullOrWhiteSpace(value))
                {
                    return "";
                }

                return value.Trim().TrimEnd('\\');
            }
        }

        private sealed class ApiEndpoint
        {
            public string Url { get; private set; }
            public string Host { get; private set; }
            public int Port { get; private set; }
            public bool IsValid { get; private set; }
            public string ErrorMessage { get; private set; }

            public static ApiEndpoint Valid(string url, string host, int port)
            {
                return new ApiEndpoint
                {
                    Url = url ?? "",
                    Host = host ?? "",
                    Port = port,
                    IsValid = true,
                    ErrorMessage = ""
                };
            }

            public static ApiEndpoint Invalid(string url, string errorMessage)
            {
                return new ApiEndpoint
                {
                    Url = url ?? "",
                    Host = "",
                    Port = 0,
                    IsValid = false,
                    ErrorMessage = errorMessage ?? "unknown URL error"
                };
            }
        }

        private sealed class ApiModelsProbe
        {
            public string ConfiguredApiUrl { get; set; }
            public string ModelsEndpoint { get; set; }
            public int HttpStatus { get; set; }
            public string HttpStatusText { get; set; }
            public bool HttpReachable { get; set; }
            public bool JsonValid { get; set; }
            public bool HasDataArray { get; set; }
            public int ModelCount { get; set; }
            public string[] ModelIds { get; set; }
            public string ErrorMessage { get; set; }

            public bool IsReady
            {
                get
                {
                    return HttpStatus == 200 && JsonValid && HasDataArray && ModelCount >= 1;
                }
            }
        }

        private sealed class ApiEndpointSelection
        {
            public ApiModelsProbe PrimaryProbe { get; set; }
            public ApiModelsProbe[] FallbackProbes { get; set; }
            public ApiModelsProbe SelectedProbe { get; set; }

            public bool IsReady
            {
                get
                {
                    return SelectedProbe != null && SelectedProbe.IsReady;
                }
            }
        }

        private sealed class PortListener
        {
            public int Pid { get; private set; }
            public string ProcessName { get; private set; }
            public string ExecutablePath { get; private set; }
            public string LocalEndpoint { get; private set; }

            public static PortListener FromPid(int pid, string localEndpoint)
            {
                string processName = "UNKNOWN";
                string executablePath = "UNKNOWN";

                try
                {
                    using (Process process = Process.GetProcessById(pid))
                    {
                        processName = string.IsNullOrWhiteSpace(process.ProcessName) ? "UNKNOWN" : process.ProcessName;
                        try
                        {
                            executablePath = process.MainModule == null || string.IsNullOrWhiteSpace(process.MainModule.FileName)
                                ? "UNKNOWN"
                                : process.MainModule.FileName;
                        }
                        catch
                        {
                            executablePath = "UNKNOWN";
                        }
                    }
                }
                catch
                {
                    processName = "UNKNOWN";
                    executablePath = "UNKNOWN";
                }

                return new PortListener
                {
                    Pid = pid,
                    ProcessName = processName,
                    ExecutablePath = executablePath,
                    LocalEndpoint = localEndpoint ?? ""
                };
            }
        }

        private sealed class ConfigLoadResult
        {
            public LauncherConfig Config { get; private set; }
            public bool IsValid { get; private set; }
            public bool Created { get; private set; }
            public string ErrorMessage { get; private set; }

            public static ConfigLoadResult Valid(LauncherConfig config, bool created)
            {
                return new ConfigLoadResult
                {
                    Config = config,
                    IsValid = true,
                    Created = created,
                    ErrorMessage = ""
                };
            }

            public static ConfigLoadResult Invalid(LauncherConfig fallbackConfig, string errorMessage)
            {
                return new ConfigLoadResult
                {
                    Config = fallbackConfig,
                    IsValid = false,
                    Created = false,
                    ErrorMessage = errorMessage ?? "unknown config error"
                };
            }
        }

        private sealed class LauncherConfig
        {
            public int Version { get; set; }
            public string MstyApiUrl { get; set; }
            public string ConsensusExePath { get; set; }
            public string LogDir { get; set; }
            public int StartupDelayMinSeconds { get; set; }
            public int StartupDelayMaxSeconds { get; set; }
            public int StaleRecoveryTimeoutSeconds { get; set; }
            public int StaleRelaunchDelayMinSeconds { get; set; }
            public int StaleRelaunchDelayMaxSeconds { get; set; }
            public string MstyWindowMode { get; set; }
            public string[] KnownMstyProcessNames { get; set; }
            public bool EnableStaleRecovery { get; set; }
            public int LogRetentionDays { get; set; }
            public int MaxLogFiles { get; set; }
            public string[] FallbackMstyApiUrls { get; set; }
            public bool AllowFallbackApi { get; set; }
            public Dictionary<string, string> ConsensusEnvironmentVariables { get; set; }
            public bool EnableConsensusEnvironmentInjection { get; set; }

            public static LauncherConfig CreateDefault()
            {
                return new LauncherConfig
                {
                    Version = 1,
                    MstyApiUrl = DefaultMstyApiUrl,
                    ConsensusExePath = DefaultConsensusExePath,
                    LogDir = DefaultLogDir,
                    StartupDelayMinSeconds = 20,
                    StartupDelayMaxSeconds = 90,
                    StaleRecoveryTimeoutSeconds = 240,
                    StaleRelaunchDelayMinSeconds = 3,
                    StaleRelaunchDelayMaxSeconds = 5,
                    MstyWindowMode = "hidden",
                    KnownMstyProcessNames = new[] { "MstyGo", "MstyClaw", "MstyStudio", "msty-llama-server" },
                    EnableStaleRecovery = true,
                    LogRetentionDays = 14,
                    MaxLogFiles = 30,
                    FallbackMstyApiUrls = new[] { "http://127.0.0.1:11454" },
                    AllowFallbackApi = true,
                    ConsensusEnvironmentVariables = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
                    {
                        { "CONSENSUS_MSTY_BASE_URL", "{selected_msty_api_url}" },
                        { "AURELIUS_MSTY_BASE_URL", "{selected_msty_api_url}" },
                        { "MSTY_BASE_URL", "{selected_msty_api_url}" }
                    },
                    EnableConsensusEnvironmentInjection = true
                };
            }

            public void Normalize()
            {
                if (StartupDelayMinSeconds < 0 || StartupDelayMaxSeconds < 0)
                {
                    throw new FormatException("startup delay values must be non-negative.");
                }
                if (StaleRecoveryTimeoutSeconds <= 0)
                {
                    throw new FormatException("stale_recovery_timeout_seconds must be greater than zero.");
                }
                if (StaleRelaunchDelayMinSeconds < 0 || StaleRelaunchDelayMaxSeconds < 0)
                {
                    throw new FormatException("stale relaunch delay values must be non-negative.");
                }
                if (StartupDelayMaxSeconds < StartupDelayMinSeconds)
                {
                    int temp = StartupDelayMinSeconds;
                    StartupDelayMinSeconds = StartupDelayMaxSeconds;
                    StartupDelayMaxSeconds = temp;
                }
                if (StaleRelaunchDelayMaxSeconds < StaleRelaunchDelayMinSeconds)
                {
                    int temp = StaleRelaunchDelayMinSeconds;
                    StaleRelaunchDelayMinSeconds = StaleRelaunchDelayMaxSeconds;
                    StaleRelaunchDelayMaxSeconds = temp;
                }
                if (KnownMstyProcessNames == null || KnownMstyProcessNames.Length == 0)
                {
                    throw new FormatException("known_msty_process_names must include at least one process name.");
                }
                MstyWindowMode = (MstyWindowMode ?? "").Trim().ToLowerInvariant();
                if (MstyWindowMode != "normal" && MstyWindowMode != "minimized" && MstyWindowMode != "hidden")
                {
                    throw new FormatException("msty_window_mode must be one of: normal, minimized, hidden.");
                }
                if (LogRetentionDays < 1)
                {
                    throw new FormatException("log_retention_days must be at least 1.");
                }
                if (MaxLogFiles < 1)
                {
                    throw new FormatException("max_log_files must be at least 1.");
                }
                if (FallbackMstyApiUrls == null)
                {
                    FallbackMstyApiUrls = new string[0];
                }
                if (ConsensusEnvironmentVariables == null)
                {
                    ConsensusEnvironmentVariables = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
                }
                foreach (KeyValuePair<string, string> item in ConsensusEnvironmentVariables)
                {
                    if (string.IsNullOrWhiteSpace(item.Key))
                    {
                        throw new FormatException("consensus_environment_variables contains an empty environment variable name.");
                    }
                    if (item.Value == null)
                    {
                        throw new FormatException("consensus_environment_variables." + item.Key + " must be a string.");
                    }
                }
            }

            public string ToJson()
            {
                return ToJson(false);
            }

            public string ToJson(bool redactSensitiveValues)
            {
                var builder = new StringBuilder();
                builder.AppendLine("{");
                builder.AppendLine("  \"version\": " + Version + ",");
                builder.AppendLine("  \"msty_api_url\": \"" + EscapeJson(MstyApiUrl) + "\",");
                builder.AppendLine("  \"consensus_exe_path\": \"" + EscapeJson(ConsensusExePath) + "\",");
                builder.AppendLine("  \"log_dir\": \"" + EscapeJson(LogDir) + "\",");
                builder.AppendLine("  \"startup_delay_min_seconds\": " + StartupDelayMinSeconds + ",");
                builder.AppendLine("  \"startup_delay_max_seconds\": " + StartupDelayMaxSeconds + ",");
                builder.AppendLine("  \"stale_recovery_timeout_seconds\": " + StaleRecoveryTimeoutSeconds + ",");
                builder.AppendLine("  \"stale_relaunch_delay_min_seconds\": " + StaleRelaunchDelayMinSeconds + ",");
                builder.AppendLine("  \"stale_relaunch_delay_max_seconds\": " + StaleRelaunchDelayMaxSeconds + ",");
                builder.AppendLine("  \"msty_window_mode\": \"" + EscapeJson(MstyWindowMode) + "\",");
                builder.AppendLine("  \"known_msty_process_names\": [");
                for (int i = 0; i < KnownMstyProcessNames.Length; i++)
                {
                    string suffix = i == KnownMstyProcessNames.Length - 1 ? "" : ",";
                    builder.AppendLine("    \"" + EscapeJson(KnownMstyProcessNames[i]) + "\"" + suffix);
                }
                builder.AppendLine("  ],");
                builder.AppendLine("  \"enable_stale_recovery\": " + (EnableStaleRecovery ? "true" : "false") + ",");
                builder.AppendLine("  \"log_retention_days\": " + LogRetentionDays + ",");
                builder.AppendLine("  \"max_log_files\": " + MaxLogFiles + ",");
                builder.AppendLine("  \"fallback_msty_api_urls\": [");
                for (int i = 0; i < FallbackMstyApiUrls.Length; i++)
                {
                    string suffix = i == FallbackMstyApiUrls.Length - 1 ? "" : ",";
                    builder.AppendLine("    \"" + EscapeJson(FallbackMstyApiUrls[i]) + "\"" + suffix);
                }
                builder.AppendLine("  ],");
                builder.AppendLine("  \"allow_fallback_api\": " + (AllowFallbackApi ? "true" : "false") + ",");
                builder.AppendLine("  \"consensus_environment_variables\": {");
                int envIndex = 0;
                foreach (KeyValuePair<string, string> item in ConsensusEnvironmentVariables)
                {
                    string suffix = envIndex == ConsensusEnvironmentVariables.Count - 1 ? "" : ",";
                    string value = redactSensitiveValues ? RedactValueForLog(item.Key, item.Value) : item.Value;
                    builder.AppendLine("    \"" + EscapeJson(item.Key) + "\": \"" + EscapeJson(value) + "\"" + suffix);
                    envIndex++;
                }
                builder.AppendLine("  },");
                builder.AppendLine("  \"enable_consensus_environment_injection\": " + (EnableConsensusEnvironmentInjection ? "true" : "false"));
                builder.AppendLine("}");
                return builder.ToString();
            }

            private static string EscapeJson(string value)
            {
                if (value == null)
                {
                    return "";
                }

                return value
                    .Replace("\\", "\\\\")
                    .Replace("\"", "\\\"")
                    .Replace("\r", "\\r")
                    .Replace("\n", "\\n")
                    .Replace("\t", "\\t");
            }
        }

        private sealed class RuntimeStatus
        {
            public string LauncherVersion { get; private set; }
            public string MstyApiStatus { get; private set; }
            public string MstyModelsEndpoint { get; private set; }
            public bool MstyApiReady { get; private set; }
            public int MstyModelCount { get; private set; }
            public string[] MstyModelIds { get; private set; }
            public string SelectedMstyApiUrl { get; private set; }
            public bool AllowFallbackApi { get; private set; }
            public string[] FallbackMstyApiUrls { get; private set; }
            public ApiModelsProbe[] FallbackProbeResults { get; private set; }
            public string MstyWindowMode { get; private set; }
            public string ConsensusLaunchEndpoint { get; private set; }
            public Dictionary<string, string> ConsensusEnvironmentVariables { get; private set; }
            public bool EnvironmentInjectionEnabled { get; private set; }
            public string MstyProcessStatus { get; private set; }
            public string ConsensusStatus { get; private set; }
            public string StartupShortcutStatus { get; private set; }
            public string StartMenuShortcutStatus { get; private set; }
            public string StartupShortcutPath { get; private set; }
            public string StartMenuShortcutPath { get; private set; }
            public string SingleInstanceLockStatus { get; private set; }
            public int LogRetentionDays { get; private set; }
            public int MaxLogFiles { get; private set; }
            public string ConfigPath { get; private set; }
            public bool ConfigValid { get; private set; }
            public string LastLogPath { get; private set; }
            public bool CriticalPathsOk { get; private set; }
            public string MstyApiHost { get; private set; }
            public int MstyApiPort { get; private set; }
            public bool PortListenerFound { get; private set; }
            public int[] PortListenerPids { get; private set; }
            public string[] PortListenerProcesses { get; private set; }
            public string PortOwner { get; private set; }

            public static RuntimeStatus Collect()
            {
                string startupShortcut = GetStartupShortcutPath();
                string startMenuShortcut = GetStartMenuShortcutPath();
                ShortcutInfo startupInfo = ReadShortcut(startupShortcut);
                ShortcutInfo startMenuInfo = ReadShortcut(startMenuShortcut);
                ApiEndpoint endpoint = ParseApiEndpoint(Config.MstyApiUrl);
                PortListener[] listeners = endpoint.IsValid ? GetPortListeners(endpoint.Port) : new PortListener[0];
                ApiEndpointSelection selection = SelectMstyApiEndpoint(3, false);
                ApiModelsProbe modelsProbe = selection.SelectedProbe ?? selection.PrimaryProbe;

                bool consensusExists = File.Exists(Config.ConsensusExePath);
                bool logDirExists = Directory.Exists(Config.LogDir);
                return new RuntimeStatus
                {
                    LauncherVersion = Program.LauncherVersion,
                    MstyApiStatus = modelsProbe.IsReady ? "READY" : "NOT_READY",
                    MstyModelsEndpoint = modelsProbe.ModelsEndpoint,
                    MstyApiReady = modelsProbe.IsReady,
                    MstyModelCount = modelsProbe.HttpReachable && modelsProbe.JsonValid && modelsProbe.HasDataArray ? modelsProbe.ModelCount : -1,
                    MstyModelIds = modelsProbe.ModelIds ?? new string[0],
                    SelectedMstyApiUrl = selection.SelectedProbe == null ? "NONE" : selection.SelectedProbe.ConfiguredApiUrl,
                    AllowFallbackApi = Config.AllowFallbackApi,
                    FallbackMstyApiUrls = Config.FallbackMstyApiUrls ?? new string[0],
                    FallbackProbeResults = selection.FallbackProbes ?? new ApiModelsProbe[0],
                    MstyWindowMode = Config.MstyWindowMode,
                    ConsensusLaunchEndpoint = selection.SelectedProbe == null ? "NONE" : selection.SelectedProbe.ConfiguredApiUrl,
                    ConsensusEnvironmentVariables = Config.ConsensusEnvironmentVariables ?? new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase),
                    EnvironmentInjectionEnabled = Config.EnableConsensusEnvironmentInjection,
                    MstyProcessStatus = IsMstyRunning(false) ? "RUNNING" : "NOT_RUNNING",
                    ConsensusStatus = IsConsensusRunning(false) ? "RUNNING" : "NOT_RUNNING",
                    StartupShortcutStatus = GetShortcutStatus(startupInfo, LauncherExePath, "--startup", LauncherWorkingDirectory),
                    StartMenuShortcutStatus = GetShortcutStatus(startMenuInfo, LauncherExePath, "", LauncherWorkingDirectory),
                    StartupShortcutPath = startupShortcut,
                    StartMenuShortcutPath = startMenuShortcut,
                    SingleInstanceLockStatus = "ACQUIRED",
                    LogRetentionDays = Config.LogRetentionDays,
                    MaxLogFiles = Config.MaxLogFiles,
                    ConfigPath = Program.ConfigPath,
                    ConfigValid = ConfigState.IsValid,
                    LastLogPath = CurrentLogPath(),
                    CriticalPathsOk = ConfigState.IsValid && consensusExists && logDirExists,
                    MstyApiHost = endpoint.IsValid ? endpoint.Host : "",
                    MstyApiPort = endpoint.IsValid ? endpoint.Port : 0,
                    PortListenerFound = listeners.Length > 0,
                    PortListenerPids = listeners.Select(listener => listener.Pid).ToArray(),
                    PortListenerProcesses = listeners.Select(listener => listener.ProcessName).ToArray(),
                    PortOwner = listeners.Length > 0 ? string.Join(", ", listeners.Select(listener => listener.ProcessName).Distinct().ToArray()) : "NONE"
                };
            }

            public string ToJson()
            {
                return "{" +
                    "\"launcher_version\":\"" + EscapeJson(LauncherVersion) + "\"," +
                    "\"msty_api\":\"" + EscapeJson(MstyApiStatus) + "\"," +
                    "\"msty_models_endpoint\":\"" + EscapeJson(MstyModelsEndpoint) + "\"," +
                    "\"msty_api_ready\":" + (MstyApiReady ? "true" : "false") + "," +
                    "\"msty_model_count\":" + MstyModelCount + "," +
                    "\"msty_model_ids\":" + JsonStringArray(MstyModelIds) + "," +
                    "\"selected_msty_api_url\":\"" + EscapeJson(SelectedMstyApiUrl) + "\"," +
                    "\"allow_fallback_api\":" + (AllowFallbackApi ? "true" : "false") + "," +
                    "\"fallback_msty_api_urls\":" + JsonStringArray(FallbackMstyApiUrls) + "," +
                    "\"fallback_probe_results\":" + JsonProbeResults(FallbackProbeResults) + "," +
                    "\"msty_window_mode\":\"" + EscapeJson(MstyWindowMode) + "\"," +
                    "\"consensus_launch_endpoint\":\"" + EscapeJson(ConsensusLaunchEndpoint) + "\"," +
                    "\"consensus_environment_variables\":" + JsonStringDictionary(ConsensusEnvironmentVariables, true) + "," +
                    "\"environment_injection_enabled\":" + (EnvironmentInjectionEnabled ? "true" : "false") + "," +
                    "\"known_msty_process\":\"" + EscapeJson(MstyProcessStatus) + "\"," +
                    "\"consensus_exe\":\"" + EscapeJson(ConsensusStatus) + "\"," +
                    "\"startup_shortcut\":\"" + EscapeJson(StartupShortcutStatus) + "\"," +
                    "\"start_menu_shortcut\":\"" + EscapeJson(StartMenuShortcutStatus) + "\"," +
                    "\"startup_shortcut_status\":\"" + EscapeJson(StartupShortcutStatus) + "\"," +
                    "\"start_menu_shortcut_status\":\"" + EscapeJson(StartMenuShortcutStatus) + "\"," +
                    "\"startup_shortcut_path\":\"" + EscapeJson(StartupShortcutPath) + "\"," +
                    "\"start_menu_shortcut_path\":\"" + EscapeJson(StartMenuShortcutPath) + "\"," +
                    "\"single_instance_lock\":\"" + EscapeJson(SingleInstanceLockStatus) + "\"," +
                    "\"msty_api_host\":\"" + EscapeJson(MstyApiHost) + "\"," +
                    "\"msty_api_port\":" + MstyApiPort + "," +
                    "\"port_listener_found\":" + (PortListenerFound ? "true" : "false") + "," +
                    "\"port_listener_pids\":" + JsonIntArray(PortListenerPids) + "," +
                    "\"port_listener_processes\":" + JsonStringArray(PortListenerProcesses) + "," +
                    "\"log_retention_days\":" + LogRetentionDays + "," +
                    "\"max_log_files\":" + MaxLogFiles + "," +
                    "\"config_path\":\"" + EscapeJson(ConfigPath) + "\"," +
                    "\"config_valid\":" + (ConfigValid ? "true" : "false") + "," +
                    "\"last_log_path\":\"" + EscapeJson(LastLogPath) + "\"," +
                    "\"critical_paths_ok\":" + (CriticalPathsOk ? "true" : "false") +
                    "}";
            }

            private static string EscapeJson(string value)
            {
                if (value == null)
                {
                    return "";
                }

                return value
                    .Replace("\\", "\\\\")
                    .Replace("\"", "\\\"")
                    .Replace("\r", "\\r")
                    .Replace("\n", "\\n")
                    .Replace("\t", "\\t");
            }
        }
    }
}
