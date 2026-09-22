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
    @Published var busy: Set<Provider> = []
    @Published var local: [Provider: [LocalUsageRow]] = [:]
    @Published var localEnabled: Set<Provider> = []
    private let broker = CredentialBroker(vault: KeychainVault(), transport: RestrictedUsageTransport())
    private var tasks: [Provider: Task<Void, Never>] = [:]
    private var generation: [Provider: Int] = [:]

    func connect(_ provider: Provider, token: String, account: String) {
        do {
            let credential = try AccessCredential(token: token, accountID: account)
            disable(provider)
            try broker.connect(provider, credential: credential)
            enabled.insert(provider); errors[provider] = nil
            refresh(provider)
        } catch { errors[provider] = (error as? SafeError ?? .credentials).localizedDescription }
    }
    func enableSaved(_ provider: Provider) {
        guard !busy.contains(provider) else { return }
        broker.enableSaved(provider)
        enabled.insert(provider); errors[provider] = nil
        refresh(provider)
    }
    func refresh(_ provider: Provider) {
        guard enabled.contains(provider), !busy.contains(provider) else { return }
        generation[provider, default: 0] += 1
        let version = generation[provider, default: 0]
        busy.insert(provider)
        tasks[provider] = Task {
            guard generation[provider] == version, !Task.isCancelled else { return }
            do {
                let result = try await broker.fetch(provider)
                guard generation[provider] == version else { return }
                snapshots[provider] = result; errors[provider] = nil
            } catch {
                guard generation[provider] == version else { return }
                snapshots[provider] = nil
                errors[provider] = (error as? SafeError ?? .network).localizedDescription
                enabled.remove(provider)
            }
            if generation[provider] == version { busy.remove(provider); tasks[provider] = nil }
        }
    }
    func disable(_ provider: Provider) {
        // Synchronous with UI action on the same executor: no queued revoke gap.
        broker.disable(provider)
        localEnabled.remove(provider); local[provider] = nil
        enabled.remove(provider); snapshots[provider] = nil; errors[provider] = nil; busy.remove(provider)
        generation[provider, default: 0] += 1
        tasks.removeValue(forKey: provider)?.cancel()
    }
    func remove(_ provider: Provider) {
        disable(provider)
        do { try broker.removeSaved(provider) }
        catch { errors[provider] = SafeError.credentials.localizedDescription }
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
                        Text("Your provider quotas. Explicit connections. No silent credential discovery.").foregroundStyle(.secondary)
                    }
                }
                Text("Connections start off each launch. Live requests send your access token only to that provider’s usage endpoint. No telemetry, browser cookies, CLI launches or automatic updates.")
                    .font(.callout).padding().background(.quaternary, in: RoundedRectangle(cornerRadius: 12))
                ForEach(Provider.allCases) { provider in
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Text(provider.title).font(.title2.bold())
                            Spacer()
                            if model.busy.contains(provider) { ProgressView().controlSize(.small) }
                            Text(model.enabled.contains(provider) ? "Connected this session" : "Disconnected").foregroundStyle(.secondary)
                        }
                        if let snapshot = model.snapshots[provider] {
                            ForEach(snapshot.windows) { window in
                                HStack {
                                    Text(window.id).frame(width: 85, alignment: .leading)
                                    ProgressView(value: window.usedPercent, total: 100)
                                    Text("\(window.usedPercent, specifier: "%.1f")% used").monospacedDigit().frame(width: 110)
                                }
                                if let date = window.resetsAt { Text("Resets \(date.formatted())").font(.caption).foregroundStyle(.secondary) }
                            }
                            Text("Provider-reported usage · fetched \(snapshot.fetchedAt.formatted())").font(.caption).foregroundStyle(.secondary)
                        } else {
                            Text(provider.supportsLive ? "Live subscription allowances unavailable until you explicitly connect. Local token counts cannot determine your remaining plan allowance." : provider.limitation).foregroundStyle(.secondary)
                        }
                        if let error = model.errors[provider] { Text(error).font(.callout).foregroundStyle(.orange) }
                        if provider.supportsLive { HStack {
                            Button("Connect with access token…") { viewState.connection = provider }.disabled(model.busy.contains(provider))
                            Button("Use saved token") { model.enableSaved(provider) }.disabled(model.busy.contains(provider))
                            if model.enabled.contains(provider) {
                                Button("Refresh") { model.refresh(provider) }.disabled(model.busy.contains(provider))
                                Button("Disconnect") { model.disable(provider) }
                            }
                            Menu("More") { Button("Remove saved token", role: .destructive) { model.remove(provider) } }
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
                Text("Security limits: tokens can carry more authority than viewing quotas. Keychain protects storage, not a compromised app or Mac. This review build uses an internal credential component, not an isolated helper process. No automatic refresh-token renewal; expired tokens require reconnecting.")
                    .font(.caption).foregroundStyle(.secondary)
            }.padding(28)
        }
        .sheet(item: $viewState.connection) { provider in ConnectionSheet(provider: provider) { token, account in model.connect(provider, token: token, account: account) } }
    }
}

struct ConnectionSheet: View {
    let provider: Provider
    let connect: (String, String) -> Void
    @Environment(\.dismiss) private var dismiss
    @StateObject private var entry = EnrollmentState()
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Connect \(provider.title)").font(.title2.bold())
            Text("Advanced connection: supply an existing session access token yourself. This is not a provider sign-in flow. API keys, passwords, refresh tokens and browser cookies are not supported. Format checks cannot verify token type, scope or authenticity. Endpoint compatibility has not been tested with your account.")
            Text("Saved only in ControlTower Private’s own macOS Keychain entry. The app will not read another app’s Keychain item or sign-in file. Your token is sent to:")
            Text(provider.endpoint?.absoluteString ?? "Unavailable").font(.caption.monospaced()).textSelection(.enabled)
            SecureField("Session access token", text: $entry.token)
            if provider == .codex { TextField("Optional ChatGPT account ID", text: $entry.account) }
            if provider == .gemini {
                TextField("Required Code Assist project ID", text: $entry.account)
                Text("Gemini Code Assist model quotas only—not Google AI Studio API billing or a universal Gemini subscription balance.").font(.caption)
            }
            Toggle("I understand this token may allow more than usage reads, and authorize this provider connection.", isOn: $entry.consent)
            Text("No token refresh or background polling. Refresh manually. Expired/rejected tokens disconnect the provider. Do not paste credentials into a chat or repository.").font(.caption).foregroundStyle(.secondary)
            HStack {
                Button("Cancel") { entry.token = ""; entry.account = ""; dismiss() }
                Spacer()
                Button("Save in Keychain & fetch usage") {
                    connect(entry.token, entry.account); entry.token = ""; entry.account = ""; dismiss()
                }.disabled(!entry.consent || entry.token.isEmpty)
            }
        }.padding(24).frame(width: 560)
        .onDisappear { entry.token = ""; entry.account = "" }
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
@MainActor final class EnrollmentState: ObservableObject {
    @Published var token = ""
    @Published var account = ""
    @Published var consent = false
}
@MainActor final class RateState: ObservableObject {
    @Published var inputRate = 0.0
    @Published var cachedRate = 0.0
    @Published var outputRate = 0.0
}
