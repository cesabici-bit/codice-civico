"""Hand-labeled Italian parliamentary sentences for promise detection testing.

Each sample has:
- sentence: the Italian text
- is_promise: True if the sentence contains a political promise/commitment
- notes: why it is or isn't a promise

SOURCE: Sentences modeled on real parliamentary speech patterns from
Camera dei Deputati XIX Legislatura (dati.camera.it).
"""

PROMISE_SAMPLES: list[dict] = [
    # --- PROMISES (10) ---
    {
        "sentence": "Ci impegniamo a ridurre le tasse sul lavoro entro il 2027.",
        "is_promise": True,
        "notes": "Explicit commitment verb 'ci impegniamo' + specific deadline",
    },
    {
        "sentence": "Investiremo 5 miliardi di euro nella scuola pubblica.",
        "is_promise": True,
        "notes": "Future tense '-remo' + specific amount",
    },
    {
        "sentence": "Il Governo garantirà l'accesso universale alla sanità.",
        "is_promise": True,
        "notes": "Future tense 'garantirà' + institutional subject",
    },
    {
        "sentence": "Proponiamo di abolire il canone RAI a partire dal prossimo anno.",
        "is_promise": True,
        "notes": "Commitment verb 'proponiamo' + specific action",
    },
    {
        "sentence": "Ridurremo le aliquote IRPEF per i redditi fino a 28.000 euro.",
        "is_promise": True,
        "notes": "Future tense '-remo' + specific policy detail",
    },
    {
        "sentence": "Vogliamo riformare la giustizia civile per dimezzare i tempi dei processi.",
        "is_promise": True,
        "notes": "Commitment verb 'vogliamo' + quantified goal",
    },
    {
        "sentence": "È necessario aumentare le pensioni minime a 1.000 euro al mese.",
        "is_promise": True,
        "notes": "Commitment pattern 'è necessario' + specific number",
    },
    {
        "sentence": "Dobbiamo costruire 500.000 alloggi di edilizia popolare.",
        "is_promise": True,
        "notes": "Commitment verb 'dobbiamo' + specific quantity",
    },
    {
        "sentence": "Realizzeremo un piano straordinario per le infrastrutture del Mezzogiorno.",
        "is_promise": True,
        "notes": "Future tense '-remo' + specific plan",
    },
    {
        "sentence": (
            "Intendiamo approvare la legge sulla parità salariale"
            " entro questa legislatura."
        ),
        "is_promise": True,
        "notes": "Commitment verb 'intendiamo' + specific deadline",
    },
    # --- NON-PROMISES (10) ---
    {
        "sentence": "Signor Presidente, chiedo di intervenire sull'ordine dei lavori.",
        "is_promise": False,
        "notes": "Procedural statement, no commitment",
    },
    {
        "sentence": "Il bilancio dello Stato per il 2025 ammonta a 850 miliardi.",
        "is_promise": False,
        "notes": "Factual statement about current budget",
    },
    {
        "sentence": "Ringrazio il Ministro per la sua esauriente risposta.",
        "is_promise": False,
        "notes": "Courtesy/protocol, no commitment",
    },
    {
        "sentence": "La seduta è aperta alle ore 10 e 30.",
        "is_promise": False,
        "notes": "Procedural announcement",
    },
    {
        "sentence": "Il disegno di legge è stato approvato dalla Commissione il 15 marzo.",
        "is_promise": False,
        "notes": "Past tense factual statement",
    },
    {
        "sentence": "Quale sarà l'impatto di questa misura sui conti pubblici?",
        "is_promise": False,
        "notes": "Question, not a commitment",
    },
    {
        "sentence": "L'Italia ha il debito pubblico più alto d'Europa.",
        "is_promise": False,
        "notes": "Factual/analytical statement",
    },
    {
        "sentence": "Dichiaro chiusa la votazione per appello nominale.",
        "is_promise": False,
        "notes": "Procedural declaration",
    },
    {
        "sentence": "Il collega Rossi ha giustamente ricordato i dati ISTAT.",
        "is_promise": False,
        "notes": "Reference to colleague's statement",
    },
    {
        "sentence": "Passiamo ora all'esame dell'articolo 3 del decreto-legge.",
        "is_promise": False,
        "notes": "Procedural transition",
    },
]
