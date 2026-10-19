export type Role = "owner" | "admin" | "manager" | "agent" | "viewer";

export interface Member {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface Branding {
  logo_text?: string;
  primary_color?: string;
  accent_color?: string;
  support_email?: string;
}

export interface Tenant {
  id: string;
  slug: string;
  name: string;
  custom_domain: string | null;
  status: string;
  plan_code: string;
  branding: Branding;
  default_currency: string;
  locale: string;
  timezone: string;
  region: string;
}

export interface Entitlements {
  plan_code: string;
  plan_name?: string;
  features: Record<string, boolean>;
  quotas: Record<string, number>;
}

export interface Me {
  user: Member;
  tenant: Tenant;
  entitlements: Entitlements;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: Member;
  tenant: Tenant;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface Train {
  id: string;
  number: string;
  name: string;
  train_type: string;
  source: string;
  destination: string;
  departure_time: string | null;
  arrival_time: string | null;
  days_of_week: number[];
  stops: Array<{ name: string; offset_minutes: number }>;
  total_seats: number;
  fare_cents: number;
  currency: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AvailabilityDay {
  date: string;
  runs: boolean;
  seats_left: number;
}

export interface Availability {
  train_id: string;
  total_seats: number;
  days: AvailabilityDay[];
}

export interface Passenger {
  id?: string;
  full_name: string;
  age?: number | null;
  gender?: string;
  seat_preference?: string;
  id_document?: string;
}

export interface BookingListItem {
  id: string;
  pnr: string;
  train_number: string;
  train_name: string;
  travel_date: string;
  contact_name: string;
  seats: number;
  status: string;
  total_fare_cents: number;
  currency: string;
  channel: string;
  created_at: string;
}

export interface Booking {
  id: string;
  pnr: string;
  train: { id: string; number: string; name: string; source: string; destination: string };
  travel_date: string;
  contact_name: string;
  contact_email: string;
  contact_phone: string;
  seats: number;
  status: string;
  total_fare_cents: number;
  currency: string;
  refund_status: string;
  channel: string;
  notes: string;
  cancelled_at: string | null;
  created_at: string;
  passengers: Passenger[];
}

export interface ReportOverview {
  currency: string;
  revenue: { today_cents: number; last_30d_cents: number };
  bookings: { today: number; last_30d: number };
  trains: { active: number; total: number };
  occupancy_today: { booked: number; capacity: number; rate: number };
  cancellation_rate_30d: number;
}

export interface RevenuePoint {
  day: string;
  revenue_cents: number;
  bookings: number;
}

export interface TopTrainRow {
  train_id: string;
  number: string;
  name: string;
  bookings: number;
  seats: number;
  revenue_cents: number;
}

export interface OccupancyRow {
  train_id: string;
  number: string;
  name: string;
  booked: number;
  capacity: number;
  rate: number;
}

export interface AuditEntry {
  id: string;
  actor_email: string;
  action: string;
  entity_type: string;
  entity_id: string;
  payload: Record<string, unknown>;
  ip: string;
  created_at: string;
}

export interface Subscription {
  plan_code: string;
  plan_name: string;
  status: string;
  trial_ends_at: string | null;
  billing_customer_id: string | null;
  features: Record<string, boolean>;
  quotas: Record<string, number>;
}

export interface PlanPublic {
  code: string;
  name: string;
  description: string;
  price_cents: number;
  currency: string;
  interval: string;
  features: Record<string, unknown>;
  quotas: Record<string, number>;
  sort_order: number;
}

export interface PublicTenant {
  slug: string;
  name: string;
  status: string;
  branding: Branding;
  locale: string;
  currency: string;
  timezone: string;
  plan_code: string;
  features: Record<string, boolean>;
}
