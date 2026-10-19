import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  replace: vi.fn(),
  toast: vi.fn(),
  saveSession: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace, push: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...props }: { href: string; children: ReactNode }) => (
    <a href={typeof href === "string" ? href : "#"} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("@/components/ui/toaster", () => ({ toast: mocks.toast }));
vi.mock("@/lib/session", () => ({ saveSession: mocks.saveSession }));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    api: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
  };
});

import { ApiError, api } from "@/lib/api";
import { LoginForm } from "@/app/login/login-form";

const tenant = {
  id: "tenant-1",
  slug: "demo",
  name: "Demo Rail",
  plan_code: "growth",
  branding: { primary_color: "#112233" },
};

function renderForm(initialSlug = "demo") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <LoginForm initialSlug={initialSlug} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(api.get).mockResolvedValue(tenant);
  vi.mocked(api.post).mockReset();
  mocks.replace.mockReset();
  mocks.toast.mockReset();
  mocks.saveSession.mockReset();
});

describe("LoginForm", () => {
  it("fills the demo credentials", async () => {
    const user = userEvent.setup();
    renderForm("");

    await user.click(screen.getAllByRole("button", { name: "Use demo credentials" })[0]);

    expect(screen.getByLabelText("Workspace slug")).toHaveValue("demo");
    expect(screen.getByLabelText("Email")).toHaveValue("demo@railway.demo");
    expect(screen.getByLabelText("Password")).toHaveValue("demo1234");
  });

  it("shows the resolved workspace branding line", async () => {
    renderForm();

    expect(await screen.findByText("Signing in to Demo Rail · growth plan")).toBeInTheDocument();
  });

  it("signs in, stores the session and navigates onward", async () => {
    const user = userEvent.setup();
    const tokens = {
      access_token: "access",
      refresh_token: "refresh",
      user: { full_name: "Ada Owner" },
      tenant,
    };
    vi.mocked(api.post).mockResolvedValue(tokens);
    renderForm();

    await user.type(screen.getByLabelText("Email"), "ada@acme.example");
    await user.type(screen.getByLabelText("Password"), "secret-pass");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/dashboard"));
    expect(api.post).toHaveBeenCalledWith(
      "/auth/login",
      { email: "ada@acme.example", password: "secret-pass", tenant_slug: "demo" },
      { auth: false },
    );
    expect(mocks.saveSession).toHaveBeenCalledWith(tokens);
    expect(mocks.toast).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Welcome back, Ada", variant: "success" }),
    );
  });

  it("explains an unknown workspace", async () => {
    const user = userEvent.setup();
    vi.mocked(api.post).mockRejectedValue(new ApiError(404, "not_found", "Workspace not found."));
    renderForm();

    await user.type(screen.getByLabelText("Email"), "ada@acme.example");
    await user.type(screen.getByLabelText("Password"), "secret-pass");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No workspace found with the slug “demo”.",
    );
    expect(mocks.replace).not.toHaveBeenCalled();
  });

  it("surfaces API messages and unrelated failures", async () => {
    const user = userEvent.setup();
    vi.mocked(api.post).mockRejectedValueOnce(
      new ApiError(401, "unauthorized", "Invalid email or password."),
    );
    renderForm();

    await user.type(screen.getByLabelText("Email"), "ada@acme.example");
    await user.type(screen.getByLabelText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password.");

    vi.mocked(api.post).mockRejectedValueOnce(new Error("boom"));
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Something went wrong. Please try again.",
    );
  });
});
