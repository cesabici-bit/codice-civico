export default function Footer() {
  return (
    <footer className="mt-auto border-t border-[var(--border)] bg-[var(--bg-secondary)]">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-semibold">Codice Civico</p>
            <p className="text-sm text-[var(--text-secondary)]">
              Motore di accountability civica per la politica, giustizia e spesa pubblica italiana
            </p>
          </div>
          <div className="flex flex-col gap-1 text-sm text-[var(--text-secondary)]">
            <p>Fonti dati: Camera, Senato, ANAC, Min. Giustizia, CSM</p>
            <p>
              Open source &middot;{" "}
              <a
                href="https://github.com/cesabici-bit/codice-civico"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-primary-600 dark:hover:text-primary-400"
              >
                GitHub
              </a>
              {" "}&middot; Built by{" "}
              <a
                href="https://github.com/cesabici-bit"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-primary-600 dark:hover:text-primary-400"
              >
                cesabici-bit
              </a>
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}
