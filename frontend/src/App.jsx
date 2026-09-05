import React, { useRef, useState } from 'react'
import Header from './components/Header'
import Toast from './components/Toast'
import TriggerBanner from './components/TriggerBanner'
import KpiPulse from './components/KpiPulse'
import AlertsSection from './components/AlertsSection'
import RecommendedActions from './components/RecommendedActions'
import ChatPanel from './components/ChatPanel'
import DataQualityBar from './components/DataQualityBar'
import { AuditModal, SafetyModal, DataQualityModal } from './components/Modals'
import { kpis, alerts, recommendedActions, initialIncidents } from './data'

export default function App() {
  // Trigger banner
  const [bannerDismissed, setBannerDismissed] = useState(false)
  const alert1Ref = useRef(null)
  const [alert1Highlighted, setAlert1Highlighted] = useState(false)
  const [alert1BreakdownOpen, setAlert1BreakdownOpen] = useState(false)

  const reviewAlert1 = () => {
    setAlert1BreakdownOpen(true)
    setAlert1Highlighted(true)
    setTimeout(() => {
      alert1Ref.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 50)
    setTimeout(() => setAlert1Highlighted(false), 1600)
  }

  const toggleAlert1Breakdown = () => setAlert1BreakdownOpen((v) => !v)

  // Sev-1 safety state — 7 of 18 open incidents start unacknowledged;
  // acknowledging a specific incident or the headline Sev-1 alert each decrement the shared counter.
  const [incidents, setIncidents] = useState(initialIncidents)
  const [unackCount, setUnackCount] = useState(7)
  const totalOpen = 18
  const [sev1Acked, setSev1Acked] = useState(false)

  const decrementUnack = () => setUnackCount((c) => Math.max(0, c - 1))

  const ackIncident = (id) => {
    setIncidents((list) => {
      const target = list.find((i) => i.id === id)
      if (target && !target.acked) decrementUnack()
      return list.map((i) => (i.id === id ? { ...i, acked: true } : i))
    })
    showToast(
      'Incident Acknowledged',
      '✓ Incident logged with dispatcher acknowledgement.',
    )
  }

  const ackSev1 = () => {
    if (sev1Acked) return
    setSev1Acked(true)
    decrementUnack()
    showToast(
      'Sev-1 Alert Acknowledged',
      '✓ Acknowledged just now. Incident status logged to Safety Desk.',
    )
  }

  // Recommended action approvals
  const [approvedActions, setApprovedActions] = useState({})

  const approveAction = (id, title) => {
    setApprovedActions((m) => ({ ...m, [id]: true }))
    if (id === 'act-2' && !sev1Acked) ackSev1()
    showToast(
      'Action Approved',
      '✓ Action logged to dispatch mart. Notification paged to Transport Manager.',
    )
  }

  // Approve buttons living inside alert cards (map by alert numeric id -> approved)
  const [approvedAlertActions, setApprovedAlertActions] = useState({})
  const handleApproveDirectFromAlert = (title, alertNumericIdOrBadge) => {
    // We identify by title/badge; simplest: use title as key plus mark alert card as approved via badge mapping
    setApprovedAlertActions((m) => ({ ...m, [title]: true }))
    showToast(
      'Directive Acknowledged',
      `✓ ${title || 'Operational Directive'} executed by Transport Manager.`,
    )
  }

  // Modals
  const [auditModal, setAuditModal] = useState({
    open: false,
    title: '',
    timestamp: '',
  })
  const [safetyModalOpen, setSafetyModalOpen] = useState(false)
  const [dataQualityOpen, setDataQualityOpen] = useState(false)

  const openAudit = (title) =>
    setAuditModal({
      open: true,
      title: title || 'Action Execution Confirmed',
      timestamp: new Date().toISOString(),
    })
  const openSafety = () => setSafetyModalOpen(true)

  // Toast
  const [toast, setToast] = useState(null)
  const toastTimer = useRef(null)
  function showToast(title, message) {
    setToast({ title, message })
    if (toastTimer.current) clearTimeout(toastTimer.current)
    toastTimer.current = setTimeout(() => setToast(null), 3200)
  }

  const copyVendorMessage = (vendor, otaVal) => {
    const text = `OTA for ${vendor} dropped below the 95% SLA during the current cycle (${otaVal || '91.2%'} vs 95.0% SLA). Please review delayed routes and confirm corrective action.`
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).catch(() => {})
    }
    showToast('✓ Vendor message copied to clipboard', text)
  }

  // Build alerts with per-card approval state (map alert.id -> approved) using titles for direct-approve buttons
  const alertApprovedMap = {
    1: !!approvedAlertActions['Review Vendor X penalty'],
    3: !!approvedAlertActions['Hold Vendor Y bill line'],
    4: !!approvedAlertActions['Add standby capacity Office B'],
    5: !!approvedAlertActions['Inspect CSAT Cluster'],
  }

  const pendingCount = 3 - Object.values(approvedActions).filter(Boolean).length

  return (
    <div className="bg-surface-panel font-sans text-neutral-body antialiased selection:bg-primary/20 min-h-screen">
      <Toast toast={toast} />

      <AuditModal
        open={auditModal.open}
        onClose={() => setAuditModal({ ...auditModal, open: false })}
        actionTitle={auditModal.title}
        timestamp={auditModal.timestamp}
      />
      <SafetyModal
        open={safetyModalOpen}
        onClose={() => setSafetyModalOpen(false)}
        unackCount={unackCount}
        totalOpen={totalOpen}
        incidents={incidents}
        onAckIncident={ackIncident}
      />
      <DataQualityModal
        open={dataQualityOpen}
        onClose={() => setDataQualityOpen(false)}
      />

      <Header />

      <main className="w-full pt-16 bg-surface-panel">
        <div className="flex flex-col w-full">
          <div className="px-6 py-6 flex flex-col gap-6 max-w-[1600px] mx-auto w-full">
            {/* Pipeline nav */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-neutral-muted uppercase tracking-wider">
                  Operational Pipeline
                </span>
                <span className="material-symbols-outlined text-neutral-muted text-[14px]">
                  chevron_right
                </span>
                <div className="flex items-center gap-1.5">
                  <span className="px-2 py-0.5 rounded-full text-[11px] bg-surface border border-border-light text-secondary font-semibold">
                    SENSE
                  </span>
                  <span className="text-neutral-muted text-xs">→</span>
                  <span className="px-2 py-0.5 rounded-full text-[11px] bg-error-bg text-error font-semibold animate-pulse border border-error/20">
                    ALERT
                  </span>
                  <span className="text-neutral-muted text-xs">→</span>
                  <span className="px-2 py-0.5 rounded-full text-[11px] bg-surface border border-border-light text-neutral-body font-medium">
                    REASON
                  </span>
                  <span className="text-neutral-muted text-xs">→</span>
                  <span className="px-2 py-0.5 rounded-full text-[11px] bg-surface border border-border-light text-neutral-body font-medium">
                    ASK
                  </span>
                  <span className="text-neutral-muted text-xs">→</span>
                  <span className="px-2 py-0.5 rounded-full text-[11px] bg-success-bg text-primary border border-primary/20 font-bold">
                    ACT
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-3 text-neutral-muted text-xs">
                <div className="flex items-center gap-1">
                  <span className="material-symbols-outlined text-[16px] text-neutral-muted">
                    tune
                  </span>
                  <span>Sensitivity: High (0.85σ)</span>
                </div>
                <span className="h-3 w-px bg-border-light"></span>
                <span className="text-primary font-semibold flex items-center gap-1">
                  ● 100% telemetry live
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
              <div className="xl:col-span-8 flex flex-col gap-6">
                <TriggerBanner
                  dismissed={bannerDismissed}
                  onDismiss={() => setBannerDismissed(true)}
                  onRestore={() => setBannerDismissed(false)}
                  onReview={reviewAlert1}
                  cardRef={null}
                />

                <KpiPulse
                  kpis={kpis}
                  unackCount={unackCount}
                  onOpenSafety={openSafety}
                  onAskCopilot={() => {}}
                />

                <AlertsSection
                  alerts={alerts}
                  unackCount={unackCount}
                  onCopyVendor={copyVendorMessage}
                  onApproveDirect={handleApproveDirectFromAlert}
                  approvedDirect={alertApprovedMap}
                  onOpenSafety={openSafety}
                  onAckSev1={ackSev1}
                  sev1Acked={sev1Acked}
                  alert1Ref={alert1Ref}
                  alert1Highlighted={alert1Highlighted}
                  alert1BreakdownOpen={alert1BreakdownOpen}
                  onAlert1Toggle={toggleAlert1Breakdown}
                />

                <RecommendedActions
                  actions={recommendedActions}
                  approvedMap={approvedActions}
                  pendingCount={pendingCount}
                  onApprove={approveAction}
                  onOpenSafety={openSafety}
                  onCopyVendor={copyVendorMessage}
                  onViewAudit={openAudit}
                />
              </div>

              <ChatPanel
                unackCount={unackCount}
                onOpenSafety={openSafety}
                onCopyVendor={copyVendorMessage}
              />
            </div>

            <DataQualityBar onOpen={() => setDataQualityOpen(true)} />
          </div>
        </div>
      </main>
    </div>
  )
}
