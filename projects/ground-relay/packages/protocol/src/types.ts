export type TaskStatus =
  | "open"
  | "claimed"
  | "delivered"
  | "accepted"
  | "paid"
  | "cancelled";

export type EvidenceKind = "text" | "photo" | "video" | "url" | "json";

export interface AcceptanceCriterion {
  id: string;
  description: string;
  required: boolean;
}

export interface RelayTask {
  id: string;
  title: string;
  description: string;
  poster: string;
  worker?: string;
  status: TaskStatus;
  rewardAtomic: string;
  rewardMint: string;
  createdAt: string;
  expiresAt?: string;
  criteria: AcceptanceCriterion[];
  callbackUrl?: string;
  evidenceHash?: string;
  settlementSignature?: string;
}

export interface EvidenceItem {
  kind: EvidenceKind;
  uri?: string;
  sha256: string;
  note?: string;
}

export interface Delivery {
  taskId: string;
  worker: string;
  submittedAt: string;
  evidence: EvidenceItem[];
  bundleHash: string;
}

export interface VerificationDecision {
  taskId: string;
  accepted: boolean;
  reason?: string;
  verifier: string;
  decidedAt: string;
}

export interface ResumeCallback {
  taskId: string;
  status: "accepted" | "paid" | "cancelled";
  evidenceHash?: string;
  settlementSignature?: string;
}
