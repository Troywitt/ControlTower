import SwiftUI
import AppKit
import LocalUsageCore
import UniformTypeIdentifiers

@main
struct ControlTowerPrivateApp: App {
    @StateObject private var model = DashboardModel()
    var body: some Scene {
        WindowGroup("ControlTower Private") { Dashboard(model: model).frame(minWidth: 720, minHeight: 600) }
        MenuBarExtra("ControlTower Private", systemImage: "chart.bar.xaxis") {
            Text("Explicit connections · no automatic sign-in")
            Button("Open dashboard") { NSApp.activate(ignoringOtherApps: true); NSApp.windows.first?.makeKeyAndOrderFront(nil) }
            Divider()
            Button("Quit") { NSApp.terminate(nil) }
        }
    }
}

@MainActor
final class DashboardModel: ObservableObject {
    @Published var enabled: Set<Provider> = []
    @Published var snapshots: [Provider: QuotaSnapshot] = [:]
    @Published var errors: [Provider: String] = [:]
    @Published var local: [Provider: [LocalUsageRow]] = [:]
    @Published var localEnabled: Set<Provider> = []
    private var feedFolders: [Provider: URL] = [:]
    private var timer: Timer?

    func selectFeed(_ provider: Provider) {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true; panel.canChooseFiles = false; panel.allowsMultipleSelection = false
        panel.message = "Choose only the dedicated ControlTower quota-feed folder, never a provider sign-in or project folder. Access ends when you disconnect or quit."
        guard panel.runModal() == .OK, let folder = panel.url else { return }
        disable(provider)
        guard folder.startAccessingSecurityScopedResource() else {
            errors[provider] = "Folder access was not granted. Select the dedicated quota folder again."; return
        }
        feedFolders[provider] = folder
        enabled.insert(provider)
        refresh(provider)
        if timer == nil {
            timer = Timer.scheduledTimer(withTimeInterval: 5, repeats: true) { [weak self] _ in
                Task { @MainActor in
                    guard let self else { return }
                    for provider in self.enabled { self.refresh(provider) }
                }
            }
        }
    }
    func refresh(_ provider: Provider) {
        guard enabled.contains(provider), let folder = feedFolders[provider] else { return }
        do {
            let result = try QuotaFeed.decode(SelectedFile.read(folder.appendingPathComponent(provider.rawValue + ".json")), provider: provider)
            snapshots[provider] = result
            errors[provider] = result.windows.isEmpty ? "Provider quota unavailable. Complete setup or refresh in the official provider adapter." : nil
        } catch {
            snapshots[provider] = nil
            errors[provider] = "Quota feed unavailable or invalid. Waiting for the adapter; no credentials were read."
        }
    }
    func disable(_ provider: Provider) {
        if let folder = feedFolders.removeValue(forKey: provider) { folder.stopAccessingSecurityScopedResource() }
        enabled.remove(provider); snapshots[provider] = nil; errors[provider] = nil
        localEnabled.remove(provider); local[provider] = nil
        if enabled.isEmpty { timer?.invalidate(); timer = nil }
    }
    func importUsage(_ provider: Provider) {
        guard localEnabled.contains(provider) else { return }
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.json]; panel.canChooseDirectories = false; panel.allowsMultipleSelection = false
        panel.message = "Choose a usage aggregate JSON export. Do not select sign-in credentials or a transcript. Data stays in memory until you clear it or quit."
        guard panel.runModal() == .OK, let url = panel.url else { return }
        do { local[provider] = try AggregateImporter.load(provider: provider, enabled: localEnabled.contains(provider)) { try SelectedFile.read(url) } }
        catch { errors[provider] = (error as? SafeError ?? .file).localizedDescription }
    }
}

struct Dashboard: View {
    @ObservedObject var model: DashboardModel
    @StateObject private var viewState = DashboardViewState()
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                HStack {
                    Image(systemName: "lock.shield").font(.largeTitle).foregroundStyle(.teal)
                    VStack(alignment: .leading) {
                        Text("ControlTower Private").font(.largeTitle.bold())
                        Text("Provider-owned sign-in. Quota numbers stay local.").foregroundStyle(.secondary)
                    }
                }
                Text("Connections start off each launch. Select a dedicated quota-feed folder after setup. The dashboard reads only Claude/Codex/Gemini/Grok quota snapshots every five seconds. It does not sign in, receive tokens, launch providers or access the network.")
                    .font(.callout).padding().background(.quaternary, in: RoundedRectangle(cornerRadius: 12))
                ForEach(Provider.allCases) { provider in
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Text(provider.title).font(.title2.bold())
                            Spacer()
                            Text(model.enabled.contains(provider) ? "Watching quota feed" : "Disconnected").foregroundStyle(.secondary)
                        }
                        if let snapshot = model.snapshots[provider] {
                            ForEach(snapshot.windows) { window in
                                HStack {
                                    Text(window.id).frame(width: 85, alignment: .leading)
                                    ProgressView(value: window.usedPercent, total: 100)
                                    Text("\(window.usedPercent, specifier: "%.1f")% used").monospacedDigit().frame(width: 110)
                                }
                                if let date = window.resetsAt { Text("\([.gemini, .grok].contains(provider) ? "Estimated reset" : "Resets") \(date.formatted())").font(.caption).foregroundStyle(.secondary) }
                            }
                            Text("Provider observation · \(snapshot.fetchedAt.formatted())").font(.caption).foregroundStyle(.secondary)
                            if provider == .gemini { Text("Official CLI screen observation; provider data may be cached. Rounded tier usage and estimated reset times.").font(.caption).foregroundStyle(.secondary) }
                            if provider == .grok { Text("SuperGrok weekly pool observed in official CLI. Floored percentage; reset inferred from local display. Provider data may be cached.").font(.caption).foregroundStyle(.secondary) }
                            if Date().timeIntervalSince(snapshot.fetchedAt) > QuotaFeed.staleAfter {
                                Text("Stale — last observation is over five minutes old. Current allowance is unknown; refresh through the provider adapter.").font(.callout).foregroundStyle(.orange)
                            }
                        } else {
                            Text(providerSetup(provider)).foregroundStyle(.secondary)
                        }
                        if let error = model.errors[provider] { Text(error).font(.callout).foregroundStyle(.orange) }
                        if [.claude, .codex, .gemini, .grok].contains(provider) { HStack {
                            Button("Setup instructions…") { viewState.connection = provider }
                            Button("Choose quota-feed folder…") { model.selectFeed(provider) }
                            if model.enabled.contains(provider) {
                                Button("Read snapshot") { model.refresh(provider) }
                                Button("Disconnect") { model.disable(provider) }
                            }
                        } }
                        Divider()
                        HStack {
                            Text("Local usage estimates").font(.headline)
                            Spacer()
                            Toggle("Allow local import", isOn: Binding(get: { model.localEnabled.contains(provider) }, set: { on in
                                if on { model.localEnabled.insert(provider) } else { model.localEnabled.remove(provider); model.local[provider] = nil }
                            })).toggleStyle(.checkbox)
                            Button("Import aggregate JSON…") { model.importUsage(provider) }.disabled(!model.localEnabled.contains(provider))
                            if model.local[provider] != nil { Button("Clear") { model.local[provider] = nil } }
                        }
                        if let rows = model.local[provider] { LocalSummary(rows: rows) }
                        else { Text("Optional. Select a documented usage export; no folders or transcripts are scanned.").font(.caption).foregroundStyle(.secondary) }
                    }.padding(20).background(.background, in: RoundedRectangle(cornerRadius: 16)).overlay(RoundedRectangle(cornerRadius: 16).stroke(.quaternary))
                }
                Text("Security boundary: the dashboard is sandboxed and has no network entitlement. User-started adapters run separately with your user permissions. Official provider software owns sign-in and its network traffic. Disconnect stops this dashboard’s file reads; quit each Terminal helper separately to stop its process. Same-user malware can alter local files; these snapshots are not authenticated.")
                    .font(.caption).foregroundStyle(.secondary)
            }.padding(28)
        }
        .sheet(item: $viewState.connection) { provider in SetupSheet(provider: provider) }
    }
}

func providerSetup(_ provider: Provider) -> String {
    switch provider {
    case .claude: "Claude Code provides official status-line quota data after a model response (supported Pro/Max versions). Setup preserves your existing status line. No Claude token is copied. Observations may be stale while Claude is idle."
    case .codex: "A user-started helper uses official Codex device sign-in and account/rateLimits/read. Credentials stay with Codex in a separate Keychain-backed home. The helper refreshes only when you request it."
    case .gemini: "A private Terminal adapter reads the official Gemini CLI model-quota screen. Sign in with Google yourself, then enter /model. Only rounded Pro/Flash/Flash Lite percentages and estimated reset times are exported. The provider manages its own credentials in a separate home."
    case .grok: "Private Terminal adapter for the official Grok subscription /usage screen. Sign-in and live parser verification are pending. Exports weekly allowance only; API billing and extra credits are excluded."
    default: provider.limitation
    }
}

struct SetupSheet: View {
    let provider: Provider
    @Environment(\.dismiss) private var dismiss
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Set up \(provider.title)").font(.title2.bold())
            Text(providerSetup(provider))
            Text("1. Follow docs/PROVIDER-SETUP.md in the reviewed source package. Run the matching adapter yourself in Terminal; do not paste secrets into chat.")
            Text(provider == .claude
                 ? "2. Generate and review the statusLine patch. Apply it yourself; no existing Claude settings are changed by the generator. Continue normal Claude use to publish a quota observation."
                 : provider == .gemini ? "2. Open Start Gemini Quotas.command in your own Terminal. Complete Google sign-in yourself, then enter /model at the normal prompt. Leave the quota dialog visible. Ctrl+] stops the adapter."
                 : provider == .grok ? "2. Open Start Grok Quotas.command in your private Terminal. Complete official subscription sign-in yourself, then enter /usage. Leave Usage limit visible. Ctrl+] stops the adapter."
                 : "2. Review the signed Codex binary pin and start the helper with --login. Complete the official device sign-in yourself. The official process requests Keychain storage; no plaintext fallback is requested.")
            Text("3. Choose the dedicated quota-feed folder in this dashboard. The card should show the provider observation time and quota percentages. Missing data stays unavailable; older observations are marked stale.")
            Text("A folder connection alone does not prove quota access. Check that actual percentages and a recent observation appear.").font(.caption)
            Button("Done") { dismiss() }
        }.padding(24).frame(width: 560)
    }
}

struct LocalSummary: View {
    let rows: [LocalUsageRow]
    @StateObject private var rates = RateState()
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("\(rows.reduce(0) { $0 + $1.totalTokens }.formatted()) tokens in \(rows.count) imported rows")
            Text("Rates per million tokens (USD); enter your own rates. One rate set applies to all imported models.").font(.caption)
            HStack {
                TextField("Input", value: $rates.inputRate, format: .number)
                TextField("Cached input", value: $rates.cachedRate, format: .number)
                TextField("Output", value: $rates.outputRate, format: .number)
            }
            if [rates.inputRate, rates.cachedRate, rates.outputRate].allSatisfy({ $0.isFinite && $0 >= 0 && $0 <= 100000 }) && rates.inputRate + rates.cachedRate + rates.outputRate > 0 {
                let estimate = rows.reduce(0.0) { $0 + $1.estimate(inputRate: rates.inputRate, cachedRate: rates.cachedRate, outputRate: rates.outputRate) }
                Text("API-equivalent estimate: \(estimate, format: .currency(code: "USD"))")
            } else { Text("Cost estimate unavailable until valid rates are supplied.") }
            Text("Not a bill, subscription cost or quota estimate. Import replaces the previous export for this provider.").font(.caption).foregroundStyle(.secondary)
            ForEach(rows.prefix(15)) { row in
                HStack { Text(row.date); Text(row.model); Spacer(); Text(row.totalTokens.formatted()).monospacedDigit() }.font(.caption)
            }
            if rows.count > 15 { Text("Showing first 15 rows; totals include all rows.").font(.caption) }
        }
    }
}

@MainActor final class DashboardViewState: ObservableObject { @Published var connection: Provider? }
@MainActor final class RateState: ObservableObject {
    @Published var inputRate = 0.0
    @Published var cachedRate = 0.0
    @Published var outputRate = 0.0
}
