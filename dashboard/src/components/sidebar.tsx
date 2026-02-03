import Link from "next/link";

export function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-10 hidden w-60 flex-col border-r bg-background sm:flex">
      <nav className="flex flex-col items-start gap-2 p-4">
        <Link
          href="/"
          className="group flex h-9 w-full items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground"
        >
          Dashboard
        </Link>
        <Link
          href="/new"
          className="group flex h-9 w-full items-center rounded-md px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          New Video
        </Link>
        <Link
          href="#"
          className="group flex h-9 w-full items-center rounded-md px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          Settings
        </Link>
      </nav>
    </aside>
  );
}
