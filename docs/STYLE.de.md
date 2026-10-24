# Stilratgeber für deutsche Vorschriften

Dieser Ratgeber erklärt, wie der Text einer deutschen OrgSynDB-Vorschrift
formuliert wird. Er richtet sich an deutschsprachige und nicht
deutschsprachige Autorinnen und Autoren sowie an Chemikerinnen und Chemiker,
die vor allem mit englischsprachiger Literatur arbeiten.

Der Ratgeber ergänzt die [Schema-Referenz](SCHEMA.de.md), ersetzt sie aber
nicht. Das Schema legt unter anderem die Abschnittsnamen, die Spalten
`Reagenz | CAS | M (g/mol) | Menge | mmol | Äquiv.`, `kat.` für
Katalysatoren sowie Dezimalkommas im deutschen Text und Dezimalpunkte in
Zahlen des Datenblocks fest. Siehe dazu
[Abschnitte des Textes](SCHEMA.de.md#abschnitte-des-textes) und
[Sprachen und Fassungen](SCHEMA.de.md#sprachen-und-fassungen). Den
Arbeitsablauf vom Gerüst bis zur Prüfung und Vorschau beschreiben die
Anleitungen für [Markdown](AUTHORING.de.md) und
[Org](AUTHORING-ORG.de.org). Fachwörter, feste Wendungen und Mustersätze
finden Sie im [Glossar](GLOSSARY.de.md).

Die Regeln beruhen auf deutschen präparativen Lehr- und Handbüchern des
20. Jahrhunderts und auf Worthäufigkeiten im deutschen Korpus von Google
Books. Einzelheiten stehen unter [Quellen](#quellen). Die deutschen
Beispielvorschriften der Demo-Sammlung wurden bewusst nicht als Vorbild
verwendet.

## Kurzfassung

1. Schreiben Sie Arbeitsschritte im Infinitiv: „Den Rückstand in Ethanol
   (20 mL) lösen.“
2. Schreiben Sie Beobachtungen, Anmerkungen und Charakterisierungen im
   Präsens: „Die Lösung färbt sich gelb.“
3. Verwenden Sie „lassen“ nur für Vorgänge, die von selbst ablaufen:
   „abkühlen lassen“, nicht „lösen lassen“.
4. Verwenden Sie eingeführte deutsche Fachwörter statt Anglizismen:
   „Veresterung“, nicht „Esterifizierung“; „unter Rückfluss erhitzen“,
   nicht „refluxieren“.
5. Verwenden Sie heutige Schreibung und Nomenklatur: „Ethanol“, „Iod“,
   „Oxid“, „Rückfluss“ — nicht „Äthanol“, „Jod“, „Oxyd“, „Rückfluß“.
6. Verwenden Sie im Text das Dezimalkomma und ein Leerzeichen zwischen
   Zahl und Einheit: „2,5 g“, „25 °C“, „70 %“.
7. Schreiben Sie keinen Laborjargon: „am Rotationsverdampfer einengen“,
   nicht „einrotieren“.
8. Bleiben Sie innerhalb einer Vorschrift bei einer Form. Wechseln Sie
   nicht zwischen Infinitiv, „man“-Form und Passiv.

## Form der Arbeitsschritte

Schreiben Sie jeden Arbeitsschritt in Durchführung, Aufarbeitung und
Reinigung als Infinitivgruppe. Die Infinitivgruppe hat kein Subjekt.
Objekte und adverbiale Bestimmungen stehen vor dem Infinitiv am Satzende.

- „Den Rückstand in Ethanol (20 mL) lösen, die Lösung mit Wasser (5 mL)
  versetzen und im Eisbad abkühlen lassen. Den Niederschlag absaugen.“
- „Das Gemisch 3 h unter Rückfluss erhitzen.“
- „Die Innentemperatur dabei unter 5 °C halten.“

Diese Form wird in heutigen deutschen Anweisungen verwendet. Auch die
amtlichen deutschen Sicherheitshinweise der CLP-Verordnung stehen so:
P280 „Schutzhandschuhe / Schutzkleidung / Augenschutz / Gesichtsschutz
tragen.“; P210 „Von Hitze, heißen Oberflächen, Funken, offenen Flammen
sowie anderen Zündquellenarten fernhalten. Nicht rauchen.“ Wenn der
Gefahrenabschnitt P-Sätze zitiert, bleibt die Stimme der Vorschrift damit
einheitlich.

Für nicht deutschsprachige Autorinnen und Autoren ist der Infinitiv die
einfachste Form: Er ist die Wörterbuchform. Sie müssen weder konjugieren
(`wäscht`, `lässt`, `gibt`) noch ein trennbares Verb aufteilen (`saugt …
ab`, `tropft … zu`). Sie brauchen kein Partizip (`abgesaugt`,
`umkristallisiert` ohne `ge-`) und müssen `wird` oder `werden` nicht an das
Subjekt anpassen. Die Form ist kurz und passt zu den nummerierten Schritten
einer Vorschrift.

### Wortstellung

Trennbare Verben bleiben im Infinitiv zusammen: „absaugen“, „zutropfen“,
„umkristallisieren“.

Verbinden Sie mehrere Vorgänge innerhalb eines Schritts in ihrer zeitlichen
Reihenfolge mit Kommas und „und“. Setzen Sie „nicht“ unmittelbar vor den
Infinitiv: „Den Kolben nicht verschließen.“

Schreiben Sie Bedingungen und Endpunkte als Nebensätze mit einem finiten
Verb im Präsens. Verwenden Sie das Perfekt, wenn der Abschluss gemeint ist:
„rühren, bis die Gasentwicklung aufhört“; „rühren, bis sich der Feststoff
gelöst hat“. Verwenden Sie nie das Präteritum. Eine Bedingung darf mit
Verb-Erst-Stellung beginnen: „Kristallisiert nichts aus, die Kolbenwand mit
einem Glasstab anreiben.“

Eine Beobachtung innerhalb eines Schritts erhält einen eigenen Satz oder
Teilsatz im Präsens. Trennen Sie ihn durch Semikolon oder Punkt von der
Anweisung: „Das Natriumhydrid portionsweise eintragen; dabei entweicht
Wasserstoff.“

### Nicht verwendete Formen

- Der Sie-Imperativ, etwa „Lösen Sie …“, spricht die lesende Person an.
  Deutsche präparative Literatur verwendet ihn nicht. Die Anleitungen in
  `docs/` sprechen Autorinnen und Autoren an; die Vorschriften tun das
  nicht.
- Die „man“-Form, etwa „Man löst …“, ist eine klassische, aber veraltete
  Lehrbuchform. Sie verlangt Konjugation und getrennte Verben.
- Das Passiv Präsens, etwa „… wird gelöst“, ist ebenfalls klassisch. Es
  verlangt Partizipien und Kongruenz.
- Das Präteritum, etwa „… wurde gelöst“ oder „man löste“, gehört in einen
  experimentellen Zeitschriftenbericht über ausgeführte Arbeiten. Eine
  Vorschrift weist zu einer Arbeit an.
- Die „wir“-Form wird nicht verwendet.

Mischen Sie diese Formen nicht innerhalb einer Vorschrift.

Die historischen Zahlen zeigen, warum ältere Quellen anders klingen. Sie
stammen aus einer heuristischen Klassifikation von OCR-Text. Die Treffer
für Infinitive wurden von Hand geprüft und waren keine Anweisungen.

| Quelle | klassifizierte Sätze | man + Präsens | Passiv Präsens | sonst |
|---|---:|---:|---:|---|
| Fischer 1922 | 356 | 35 % | 64 % | Passiv Präteritum < 1 % |
| Gattermann 1921 | 795 | 76 % | 17 % | man + Konjunktiv 6 % |
| Lassar-Cohn 1906 | 494 | 63 % | 26 % | Passiv Präteritum 5 % |
| Houben 1922 | 1391 | 61 % | 34 % | Passiv Präteritum 4 % |

Keine dieser Quellen verwendet den bloßen Infinitiv für Anweisungen. Im
Korpus stehen „filtriert man“ und „wird filtriert“ je 10⁹ Wörter für
1950–1974 im Verhältnis 131 zu 112 und für 1975–1999 im Verhältnis 6,0 zu
11,4. Nach 1975 gewinnt damit das Passiv. Dieser Ratgeber weicht bewusst
von den historischen Formen ab. Wer ältere Literatur liest, muss die
„man“-Form, das Passiv und den Konjunktiv dennoch erkennen.

### „lassen“

„lassen“ mit Infinitiv bedeutet, dass etwas geschehen darf oder von
jemandem ausgeführt wird. „Den Feststoff lösen lassen“ heißt deshalb, dass
jemand anderes den Feststoff lösen soll.

Verwenden Sie die Form nur für Vorgänge, die nach dem Anstoßen von selbst
ablaufen: „abkühlen lassen“, „über Nacht stehen lassen“, „absitzen lassen“,
„die Phasen sich trennen lassen“, „das Gemisch sich auf Raumtemperatur erwärmen
lassen“, „auskristallisieren lassen“.

Für eine Tätigkeit der ausführenden Person verwenden Sie das einfache
Verb: „lösen“. Für den Endpunkt verwenden Sie einen `bis`-Satz: „rühren,
bis sich der Feststoff gelöst hat“. Schreiben Sie nicht „auf RT kommen
lassen“, sondern „sich auf Raumtemperatur erwärmen lassen“.

### Mengen im Text

Nennen Sie einen Stoff bei der ersten Erwähnung in einem Schritt und setzen
Sie seine Menge in Klammern dahinter. Geben Sie wie in der
Reagenzientabelle zuerst Masse oder Volumen und dann die Stoffmenge an:
„Benzaldehyd (5,31 g, 50,0 mmol)“. Verwenden Sie bei späteren Erwähnungen
den bestimmten Artikel ohne Mengenangabe: „den Benzaldehyd“.

Ältere deutsche Literatur setzt die Menge vor den Stoff: „20 g Anilin
werden mit 30 g Eisessig … gekocht“, Fischer 1922. Erkennen Sie diese Form,
aber übernehmen Sie sie nicht. Schreiben Sie wiederholte Portionen als
„dreimal mit Ethylacetat (je 30 mL) extrahieren“ oder „(3 × 30 mL)“.

### Präpositionen und feste Verbindungen

Die vollständige Auswahl steht im Abschnitt „Feste Wendungen“ des
[Glossars](GLOSSARY.de.md#feste-wendungen).

- Eine Zieltemperatur folgt auf „auf“, eine Haltetemperatur auf „bei“:
  „auf 0 °C kühlen“, „bei 0 °C rühren“.
- Schreiben Sie „aus Ethanol umkristallisieren“, nicht „in“.
- Schreiben Sie „über Natriumsulfat trocknen“ und „über Kieselgur
  filtrieren“, nicht „durch“. Ein Filter steht dagegen mit „durch“:
  „durch ein Faltenfilter filtrieren“.
- Schreiben Sie „in Dichlormethan aufnehmen“, „mit Wasser versetzen“ und
  „mit Ethylacetat extrahieren“.
- Verwenden Sie „unter Rühren“, „unter Rückfluss“, „unter Eiskühlung“,
  „unter Argon“, „unter vermindertem Druck“ sowie „im Vakuum“, „im
  Eisbad“, „im Abzug“.
- „innerhalb von 30 min zutropfen“ bedeutet, dass sich die Zugabe über
  30 min verteilt.
- „zutropfen“ bedeutet bereits tropfenweise. Schreiben Sie nicht
  „tropfenweise zutropfen“.
- Schreiben Sie „zur Trockne eindampfen“, nicht „zur Trockenheit“.

### Satzbau

Beschränken Sie einen Satz auf einen Vorgang oder wenige eng verbundene
Vorgänge. Verwenden Sie höchstens eine Ebene eines erweiterten
Partizipialattributs. Teilen Sie „die mit 20 mL kaltem Wasser gewaschenen
und im Vakuum getrockneten Kristalle“ in einzelne Schritte. Bevorzugen Sie
Verben vor Nominalisierungen. „nach dem Abkühlen“ ist eine feste Wendung
und in Ordnung; vermeiden Sie „Durchführung der Abkühlung“.

## Tempus und Form der übrigen Abschnitte

Alles, was keine Anweisung ist, steht im Präsens.

- **Zusammenfassung:** Schreiben Sie ein bis drei Sätze im Präsens und
  nennen Sie Produkt, Reaktion und Methode: „Isopentylacetat entsteht
  durch Fischer-Veresterung von Isopentylalkohol mit Eisessig.“ Auch ein
  nominaler erster Satz ist üblich: „Darstellung von X aus Y durch …“.
- **Beobachtungen:** Verwenden Sie den Präsens-Indikativ und den Stoff als
  Subjekt: „Die Lösung färbt sich tiefrot.“, „Es entsteht ein farbloser
  Niederschlag.“
- **Charakterisierung:** Schreiben Sie Daten im Nominalstil: „Farblose
  Nadeln, Smp. 134–136 °C (Lit. 135 °C).“ Aussagen stehen im Präsens:
  „Das IR-Spektrum zeigt …“
- **Anmerkungen:** Erklärungen stehen im Präsens: „Die Veresterung ist eine
  Gleichgewichtsreaktion; …“ Ratschläge stehen im Infinitiv: „Das Produkt
  nur schonend erwärmen.“ Modalverben wie „muss“, „darf nicht“ und „kann“
  sind möglich. Einen einzelnen vergangenen Vorgang, etwa einen
  fehlgeschlagenen Ansatz, können Sie bei Bedarf im Perfekt nennen.
  Formulieren Sie ihn sonst als allgemeine Aussage: „Die Ausbeute sinkt,
  wenn das THF nicht trocken ist.“
- **Gefahren und Entsorgung:** Verwenden Sie, soweit zutreffend, den
  amtlichen deutschen Wortlaut der CLP-Gefahrenhinweise: H225 „Flüssigkeit
  und Dampf leicht entzündbar.“, H314 „Verursacht schwere Verätzungen der
  Haut und schwere Augenschäden.“, H332 „Gesundheitsschädlich bei
  Einatmen.“, EUH014 „Reagiert heftig mit Wasser.“, EUH019 „Kann
  explosionsfähige Peroxide bilden.“ Maßnahmen und Entsorgung stehen wie
  die P-Sätze im Infinitiv: „Im Abzug arbeiten.“, „Die wässrigen Phasen
  neutralisieren und als wässrigen Abfall entsorgen.“ Das Feld `hazards`
  im Datenblock übernimmt denselben Wortlaut.
- **Literatur:** Zitieren Sie ein Werk in seiner Sprache. Verwenden Sie für
  deutsche Werke die deutschen bibliografischen Abkürzungen „Aufl.“,
  „Bd.“, „S.“, „Hrsg.“.

## Zahlen, Einheiten und Abkürzungen

Verwenden Sie im deutschen Text das Dezimalkomma. Zahlen im Datenblock
behalten nach dem Schema den Dezimalpunkt. Setzen Sie bei Tausendern ein
schmales Leerzeichen oder kein Trennzeichen, aber keinen Punkt: „1013 hPa“,
„12 500 g“.

Zwischen Zahl und Einheit steht ein Leerzeichen, auch vor °C und %:
„25 °C“, „70 %“, „2,5 g“. Verwenden Sie ein geschütztes Leerzeichen, wenn
der Editor es erlaubt. Das entspricht DIN 5008 und der SI-Praxis. Eine
Ausnahme sind Zusammensetzungen wie „96%ig“ oder besser „96-prozentig“. In
Vorschriften ist „Schwefelsäure (96 %)“ vorzuziehen.

Koppeln Sie Zusammensetzungen mit Zahlen vollständig durch:
„50-mL-Rundkolben“, „10-mmol-Maßstab“, „¹H-NMR-Spektrum“, „NaCl-Lösung“.

Schreiben Sie Bereiche als „70–80 °C“ mit Halbgeviertstrich und nur einer
Einheit oder als „70 bis 80 °C“. Verwenden Sie für negative Temperaturen
ein echtes Minuszeichen: „−78 °C“. Schreiben Sie einen Bereich über null
als „von −10 bis 0 °C“, damit Halbgeviertstrich und Minuszeichen nicht
verwechselt werden.

### Größen und Einheiten

- **Volumen:** Verwenden Sie „mL“. Diese Form ist neben „1“ und „I“ in
  serifenloser Schrift eindeutig. „ml“ ist die traditionelle deutsche
  Form und ebenso SI-konform. Verwenden Sie innerhalb einer Sammlung nur
  eine Form. Im Korpus 2000–2019 stehen „ml“ 13 465 und „mL“ 507 Mal je
  10⁹ Wörter. Die Empfehlung beruht daher auf Lesbarkeit, nicht auf
  Häufigkeit. `ccm` bedeutet in älterer Literatur mL.
- **Zeit:** Verwenden Sie mit Zahlen „h“, „min“ und „s“. Schreiben Sie die
  Einheit ohne Zahl aus: „einige Minuten“. Verwenden Sie nicht „Std.“ oder
  „Min.“. Ergänzen Sie bei „über Nacht“ die Dauer: „über Nacht (16 h)“.
- **Temperatur:** Schreiben Sie „Raumtemperatur“ im Text aus und verwenden
  Sie nicht „RT“. „Zimmertemperatur“ ist die ältere Bezeichnung.
  „Raumtemperatur“ überholt sie nach 1975; für 1975–1999 lauten die
  Korpuswerte 1621 und 547.
- **Druck:** Verwenden Sie mbar oder hPa; 1 hPa = 1 mbar. Geben Sie den
  Druck bei „im Vakuum“ immer an: „im Vakuum (20 mbar)“. Ältere Literatur
  verwendet Torr oder mm Hg; 1 Torr = 1,333 mbar.
- **Konzentration:** Schreiben Sie „Salzsäure (2 mol/L)“. „2 M“ ist
  gebräuchliche und verständliche Laborkurzschrift. `n` oder `N` für die
  Normalität ist veraltet. Schreiben Sie „Massenanteil“ oder, wenn
  eindeutig, schlicht „%“. Verwenden Sie nicht „Gew.-%“; diese Form ist
  nach DIN 1310 nicht normgerecht. Schreiben Sie Lösungsmittelgemische als
  „Petrolether/Ethylacetat 4:1 (v/v)“.
- **Äquivalente und Katalysatoren:** Verwenden Sie entsprechend der
  Schemaspalte „Äquiv.“ und nicht „eq.“. Katalysatoren erhalten „kat.“;
  Katalysatorbeladungen stehen in „mol-%“.
- **Ausbeute:** Schreiben Sie „Ausbeute: 4,56 g (35,0 mmol, 70 %)“.
  Verwenden Sie nicht „% d. Th.“. Das ältere „der Theorie“ ist heute
  redundant.

### Physikalische Daten

Verwenden Sie „Smp.“ für den Schmelzpunkt. Beilstein (1948) schreibt „F:“.
Für 1950–1974 war „Fp.“ mit 183 Vorkommen je 10⁹ Wörter häufiger als
„Smp.“ mit 48 und „Schmp.“ mit 26. „Fp.“ kann jedoch auch Flammpunkt
bedeuten und im Gefahrenabschnitt vorkommen. Verwenden Sie deshalb
„Smp.“; „Schmp.“ ist eine Variante. Verwenden Sie nie „Fp.“.

Verwenden Sie „Kp.“ für Siedepunkt oder Kochpunkt. Diese Form dominiert:
Im Korpus 1950–1974 stehen Kp 451 gegenüber Sdp 9 je 10⁹ Wörter;
Beilstein 1948 verwendet „Kp“. „Sdp.“ wird verstanden. Geben Sie den Druck
als „Kp. 85 °C (15 mbar)“ an. Die alte Schreibweise „Kp.₁₂“ bedeutet:
Siedepunkt bei 12 Torr.

Kennzeichnen Sie eine Zersetzung als „Zers.“: „Smp. 212 °C (Zers.)“.
„Lit.“ kennzeichnet den Literaturwert.

### Allgemeine Abkürzungen und Messdaten

Schreiben Sie „z. B.“, „ca.“ und „ggf.“; die Leerzeichen in „z. B.“ folgen
DIN 5008. Schreiben Sie im Fließtext „konzentriert“, „gesättigt“,
„verdünnt“ und „katalytisch“ aus. „konz.“, „ges.“, „verd.“ und „kat.“
gehören in Tabellen. Vermeiden Sie „min.“ für „Minimum“, weil es mit
„min“ für Minuten verwechselt werden kann.

Trennen Sie bei Spektren mit Dezimalkommas die NMR-Signale durch
Semikolons: „¹H-NMR (400 MHz, CDCl₃): δ = 4,09 (t, J = 6,8 Hz, 2 H,
OCH₂); 2,04 (s, 3 H, COCH₃).“ Verfahren Sie bei der Elementaranalyse
ebenso: „ber. C 64,58; H 10,84. gef. C 64,4; H 10,9“.

## Rechtschreibung und Nomenklatur

Verwenden Sie die heutige Rechtschreibung nach der Reform von 1996 in der
Fassung von 2006. Nach kurzem Vokal steht `ss`: „Rückfluss“, „Überschuss“,
„Feuchtigkeitsausschluss“, „lässt“, „dass“. Nach langem Vokal oder
Diphthong steht `ß`: „gießen“, „Gefäß“, „heiß“, „weiß“. Dreifache
Konsonanten bleiben erhalten: „Schlifffett“. In älterer Literatur finden
Sie „Rückfluß“, „läßt“, „daß“. Im Korpus überholt „lässt man“ die Form
„läßt man“ 2000–2019 mit 1121 zu 733.

### Chemische Schreibung

- Schreiben Sie in chemischen Namen lateinischen oder griechischen
  Ursprungs C statt K oder Z: „Calcium“, „Carbonat“, „Cyclohexan“,
  „Acetyl“, „Cyanid“. In der Allgemeinsprache kommen auch „Kalzium“,
  „Karbonat“, „Zyanid“ vor. Im Korpus 1975–1999 stehen
  „Kaliumcarbonat“ und „Kaliumkarbonat“ mit 32,8 und 18,5. Kalium,
  Natrium und Kohlenstoff behalten ihr K.
- Schreiben Sie „Iod“, nicht „Jod“. Duden führt „Jod“ als
  allgemeinsprachliche und „Iod“ als chemische Form. Entsprechend gelten
  „Iodid“ und „iodieren“.
- Verwenden Sie E statt des älteren Ä in Ethyl- und Ethernamen: „Ethanol“,
  „Diethylether“, „Ethylacetat“. Für 1975–1999 zeigt der Korpuswechsel
  Ethanol 726 gegenüber Äthanol 517, Diethylether 89 gegenüber
  Diäthyläther 44 sowie Ethylacetat 58 gegenüber Essigester 50.
- Schreiben Sie „Oxid“, nicht „Oxyd“, und „Oxidation“. Der Wechsel von
  1950–1999 zeigt für 1950–1974 Oxid 304 gegenüber Oxyd 971 und für
  1975–1999 369 gegenüber 66. Schreiben Sie „Kristall“, nicht „Krystall“.
  Der Wechsel ist bereits 1925–1949 mit 7908 gegenüber 735 erkennbar.

Behalten Sie die eingeführten Namen „Benzol“, „Toluol“, „Xylol“,
„Chloroform“, „Aceton“, „Eisessig“ und „Braunstein“. Verwenden Sie nicht
„Benzen“ oder „Toluen“; für 1975–1999 stehen Benzol 1112 und Benzen 70.

Verwenden Sie den systematischen Namen, wenn der Trivialname mehrdeutig
oder veraltet ist: „Dichlormethan“ statt „Methylenchlorid“; die
Korpuswerte 1975–1999 sind 199 und 146. Schreiben Sie „Ethylacetat“ statt
„Essigester“ und „Diethylether“ statt „Ether“ oder „Äther“ allein, denn
„Ether“ bezeichnet die Stoffklasse. Ergänzen Sie bei „Petrolether“ den
Siedebereich, etwa „Petrolether 40/60“. Verwenden Sie
„Natriumhydrogencarbonat“ statt „Natriumbicarbonat“, „Calciumchlorid“
statt „Chlorcalcium“, „Natriumcarbonat“ statt „Soda“ und
„Kaliumcarbonat“ statt „Pottasche“. Schreiben Sie „2-Propanol“;
„Isopropanol“ wird verstanden.

Verwenden Sie nie „Natron“. In älterer Literatur bezeichnete es
Natriumhydroxid, etwa bei Gattermann 1921: „einer Lösung von 2 g Natron in
4 g Wasser“. In der heutigen Alltagssprache bezeichnet es
Natriumhydrogencarbonat.

### Zusammensetzungen und Namen

Schreiben Sie eingeführte Zusammensetzungen in einem Wort;
„Natriumchloridlösung“ ist richtig. Ein Bindestrich ist bei langen oder
schwer lesbaren Zusammensetzungen erlaubt und empfohlen. Bei Formeln,
Abkürzungen und Zahlen ist er erforderlich:
„Natriumhydrogencarbonat-Lösung“, „NaCl-Lösung“, „DC-Kontrolle“,
„50-mL-Rundkolben“.

Setzen Sie bei Personennamen Bindestriche: „Liebig-Kühler“,
„Dimroth-Kühler“, „Büchner-Trichter“, „Schlenk-Kolben“,
„Grignard-Reagenz“, „Fischer-Veresterung“, „Diels-Alder-Reaktion“.
Lexikalisierte Wörter bleiben zusammengeschrieben: „Erlenmeyerkolben“.
Beide Schreibweisen sind richtig; Bindestriche erleichtern
nicht deutschsprachigen Leserinnen und Lesern die Gliederung.

Schreiben Sie Lokanten und kursive Präfixe nach IUPAC:
„3-Methylbutan-1-ol“, „tert-Butanol“, „n-Butyllithium“, „(E)“, „(R)“,
„N,N-Dimethylformamid“. Setzen Sie `n` und `tert` kursiv.

### Genus von Stoffnamen

Das grammatische Geschlecht ist für nicht deutschsprachige Personen schwer
zu erraten. Die folgenden Endungen decken die meisten Stoffnamen ab. Das
[Glossar](GLOSSARY.de.md) führt Substantive deshalb mit Artikel.

- **Neutrum, das:** Namen auf `-an`, `-en`, `-in`, `-ol`, `-on`, `-al`,
  `-at`, `-id` und `-it` sowie die meisten Elemente:
  „das Ethanol“, „das Toluol“, „das Aceton“, „das Anilin“, „das
  Natriumsulfat“, „das Natriumhydrid“, „das Iod“, „das Natrium“. Ebenfalls
  neutral sind „das Reagenz“ mit dem Plural „die Reagenzien“, „das
  Edukt“, „das Lösungsmittel“ und „das Kieselgel“.
- **Maskulinum, der:** Namen auf `-stoff`, etwa „der Wasserstoff“ und „der
  Stickstoff“, die Elemente „der Schwefel“ und „der Phosphor“ sowie „der
  Ester“, „der Ether“, „der Alkohol“, „der Aldehyd“, „der Katalysator“,
  „der Ligand“, „der Petrolether“ und „der Eisessig“.
- **Femininum, die:** Namen auf `-säure`, etwa „die Essigsäure“, und auf
  `-lauge`, etwa „die Natronlauge“, sowie „die Lösung“, „die Base“, „die
  Kieselgur“ und „die Aktivkohle“.

Schlagen Sie im Zweifel zuerst im Glossar und dann im Duden nach.
Schreiben Sie „wässrig“, nicht „wässerig“. Beide Formen sind richtig;
„wässrig“ ist die heutige Form.

## Anglizismen und Laborjargon

Verwenden Sie den Ausdruck der deutschen präparativen Literatur. Eine
Lehnübersetzung des englischen Ausdrucks wird häufig verstanden, lässt
einen Text aber übersetzt wirken. Gerade nicht deutschsprachige
Autorinnen und Autoren können solche Lehnübersetzungen schwer erkennen.
Die Ersetzungen stehen vollständig im Abschnitt
[Anglizismen und Laborjargon](GLOSSARY.de.md#anglizismen-und-laborjargon)
des Glossars.

Die Tabelle gibt relative Häufigkeiten je 10⁹ Wörter im deutschen Korpus
von Google Books als Mittelwerte der Zeiträume an.

| empfohlen | vermeiden | 1900–1924 | 1950–1974 | 1975–1999 |
|---|---|---:|---:|---:|
| Veresterung | Esterifizierung | 753 : 141 | 573 : 13 | 117 : 0,6 |
| unter Rückfluss/Rückfluß | refluxiert | 327 : 0 | 209 : 0,8 | 67 : 0,6 |
| Hydrierung | Hydrogenierung | 857 : 13 | 1741 : 11 | 433 : 7 |
| eingeengt | einrotiert | 3890 : 0,3 | 4205 : 3,7 | 2800 : 12 |
| Ausgangsmaterial | Startmaterial | 3539 : 0 | 2925 : 2,1 | 1274 : 4,5 |
| verrieben | trituriert | 2046 : 1,1 | 406 : 1,1 | 212 : 0,7 |
| Kieselgur | Celite | 949 : 2,7 | 1064 : 73 | 177 : 16 |
| Kieselgel | Silica | 13 : 51 | 581 : 85 | 300 : 65 |
| Laufmittel | Eluent | 0,2 : 0 | 200 : 2,9 | 105 : 18 |

„refluxieren“ als Infinitiv sowie „Etherifizierung“ und „geseedet“ sind
im Korpus gar nicht belegt. Belegt sind „Veretherung“ und „Verätherung“.
„Esterifizierung“ kam von 1900–1960 vor, blieb aber immer weit hinter
„Veresterung“ und ist seit 1970 fast verschwunden. Das Beispiel zeigt,
dass auch ein plausibel wirkendes Wort eine Lehnübersetzung sein kann.

Das Korpus umfasst allgemeine deutsche Bücher. Einzelne Wörter haben
andere Bedeutungen. „Kieselgel“ wird erst nach 1925 häufig; die früheren
Treffer für „Silica“ betreffen daher nicht das Chromatographiematerial.
Nach etwa 1970 verlagerte sich die deutschsprachige
Chemie-Fachpublikation ins Englische. Deshalb werden alle Chemiewörter
seltener; aussagekräftig sind die Verhältnisse, nicht die absoluten
Zahlen.

„Eluent“ hat in jüngerer Zeit aufgeholt. Für 2000–2019 lauten die Werte
Laufmittel 27, Fließmittel 69, Elutionsmittel 23 und Eluent 24. Alle vier
sind möglich; „Laufmittel“ ist das traditionelle Wort für die DC.

### Falsche Freunde

Diese Wörter ähneln englischen Wörtern, bedeuten aber etwas anderes.

- „addieren“ bedeutet zusammenzählen oder sich an eine Bindung anlagern.
  Ein Reagenz wird „zugegeben“, der Vorgang heißt „die Zugabe“.
- „kontrollieren“ bedeutet prüfen. Eine Temperatur wird „gehalten“ oder
  „geregelt“.
- „eventuell“ bedeutet „möglicherweise“, nicht „schließlich“.
- Ersetzen Sie „Präparation“ durch „Darstellung“, klassisch „Darstellung
  von X“, oder „Herstellung“. Ersetzen Sie „Prozedur“ durch „Vorschrift“.
- Schreiben Sie nicht „quenchen“, sondern nennen Sie den Vorgang: „die
  Reaktion durch Zugabe von gesättigter Ammoniumchlorid-Lösung
  abbrechen“, „überschüssiges Lithiumaluminiumhydrid mit Ethylacetat
  zersetzen“, „mit Wasser (10 mL) versetzen“. „gequencht“ erscheint im
  Korpus erst seit den 1950er-Jahren und erreicht höchstens 4 Vorkommen je
  10⁹ Wörter.
- Ersetzen Sie „Brine“ durch „gesättigte Natriumchlorid-Lösung“. Schreiben
  Sie nicht „Sole“; das ist natürliches Salzwasser.

### Laborjargon und besondere deutsche Fachwörter

Laborjargon ist im Gespräch möglich, gehört aber nicht in eine
geschriebene Vorschrift. Dazu zählen „einrotieren“, „abrotieren“,
„sekurieren“, „säulen“, „Rührfisch“, „EE“, „PE“, „DCM“, „Molsieb“,
„überkanülieren“ und „auf RT kommen lassen“. „sekurieren“ liegt im Korpus
unter 1 Vorkommen je 10⁹ Wörter. Verwenden Sie die präzisen Ersetzungen
aus dem Glossar.

Nutzen Sie auch deutsche Fachwörter, für die es keine direkte englische
Entsprechung gibt: „vorlegen“ (einen Stoff zuerst in den Kolben geben),
„absolutieren“ (ein Lösungsmittel sorgfältig wasserfrei machen), „Ansatz“
(ein einzelner Durchgang einer Reaktion), „Edukt“, „nachrühren“,
„anspringen“ (die Reaktion setzt ein), „ausölen“, „anreiben“ und
„Siedeverzug“.

Die Reaktionstypen der Website heißen „Schützung“ und „Entschützung“ und
bleiben so erhalten. Im Fließtext sind „die Schutzgruppe einführen“ und
„die Schutzgruppe abspalten“ klarer. Beide Formen werden verstanden.
„Entschützung“ wird erst nach 2000 nennenswert gedruckt; für 2000–2019
stehen 10,5 Vorkommen je 10⁹ Wörter 1,3 Vorkommen von „Abspaltung der
Schutzgruppe“ gegenüber. Zuvor war das Verhältnis umgekehrt.

## Ältere Literatur lesen und übertragen

In älteren deutschen Vorschriften, etwa bei Gattermann, im Organikum, in
Houben-Weyl, Beilstein, den Berichten oder Liebigs Annalen, begegnen Ihnen
andere Formen. Der Abschnitt
[Ältere Bezeichnungen](GLOSSARY.de.md#ältere-bezeichnungen) des Glossars
führt die heutigen Entsprechungen auf.

Erkennen Sie folgende Anweisungsformen:

- „man“ mit Präsens: „Man filtriert …“;
- Passiv Präsens: „… wird filtriert“;
- Konjunktiv I für Ratschläge und Warnungen: „Man erhitze hierbei nicht zu
  stark und nicht zu lange.“, Gattermann 1921;
- „es empfiehlt sich, … zu …“.

Zu den alten Namen und Schreibweisen gehören Äther, Alkohol, Spiritus,
Essigäther, Ligroin, Chlorcalcium, Glaubersalz, Natron, Kali, Tierkohle,
Krystall, Oxyd, Jod, „essigsaures Natrium“, „salzsaures Anilin“ sowie
Amido- und Oxy- für Amino- und Hydroxy-.

Erkennen Sie außerdem die alten Einheiten „ccm“, „Proz.“, „proz.“,
„n-Schwefelsäure“ für normal, Torr und „Kp.₁₂“. Eine bloße Angabe in „°“
meint Celsius. Der alte Dativ trägt ein `-e`: „auf dem Wasserbade“. Für
1900–1924 stehen im Korpus „Wasserbade“ 8025 und „Wasserbad“ 4212, für
1950–1974 dagegen 283 und 2251.

„bis zur stark sauren Reaktion auf Kongo“, Houben 1922, bedeutet, bis
Kongorotpapier unter pH 3 nach Blau umschlägt.

Übernehmen Sie alte Arbeitsweisen und Wörter nicht wörtlich, etwa das
Trocknen von Kristallen „auf Ton“ (auf einer porösen Platte), „Tierkohle“
oder „ausäthern“.

### Übertragungsbeispiele

1. Gattermann 1921: „Nachdem man das wässerige Destillat mit festem
   Kochsalz gesättigt hat, schüttelt man es mehrmals mit Äther aus,
   trocknet die ätherische Lösung über entwässertem Glaubersalz,
   verdampft den Äther …“
   → „Das wässrige Destillat mit festem Natriumchlorid sättigen und
   mehrmals mit Diethylether extrahieren. Die vereinigten organischen
   Phasen über wasserfreiem Natriumsulfat trocknen und den Diethylether
   abdestillieren.“
2. Fischer 1922: „Das so gewonnene Produkt wird im Vakuum über
   Chlorcalcium getrocknet.“
   → „Das Produkt im Vakuum über Calciumchlorid trocknen.“
3. Fischer 1922: „Die Gesamtausbeute beträgt etwa 33 g oder 88 Proz. der
   Theorie.“
   → „Ausbeute: 33 g (88 %).“
4. Gattermann 1921: „Man erhitze hierbei nicht zu stark und nicht zu
   lange.“
   → „Dabei nicht zu stark und nicht zu lange erhitzen.“

## Wiederverwendbare Sätze

Die [Mustersätze im Glossar](GLOSSARY.de.md#mustersätze) decken
Vorbereitung, Reaktion, Aufarbeitung, Reinigung, Charakterisierung,
Anmerkungen, Sicherheit und Entsorgung ab. Kopieren Sie den passenden
Satz, ersetzen Sie die Platzhalter `X`, `Y` und `…`, und behalten Sie das
Format der Mengenangaben bei.

## Quellen

Die historischen Werke wurden im OCR-Volltext ausgewertet: die Formen der
Anweisungen durch eine Zählung über den ganzen Text, Belegstellen durch
Suche und Stichproben.

- Fischer, Emil: *Anleitung zur Darstellung organischer Präparate*.
  10. Aufl., durchgesehen und erneut von Burckhardt Helferich.
  Braunschweig: Friedr. Vieweg & Sohn, 1922. archive.org
  `anl_darst_org_pr`.
- Gattermann, Ludwig: *Die Praxis des organischen Chemikers*. 16. Aufl.
  Berlin und Leipzig: Vereinigung wissenschaftlicher Verleger Walter de
  Gruyter & Co., 1921. archive.org
  `DiePraxisDesOrganischenChemikers1921`.
- Lassar-Cohn: *Arbeitsmethoden für organisch-chemische Laboratorien*.
  4. Aufl., Allgemeiner Teil. Hamburg und Leipzig: Leopold Voss, 1906.
  archive.org `b31359851_0001`.
- Houben, J. (Hrsg.): *Die Methoden der organischen Chemie (Weyls
  Methoden)*. 2. Aufl., Bd. 2, Spezieller Teil. Leipzig: Georg Thieme,
  1922. archive.org `methodenderorgan02houbuoft`.
- *Beilsteins Handbuch der organischen Chemie*. 4. Aufl., Zweites
  Ergänzungswerk, Bd. 8, hrsg. von Friedrich Richter. Berlin, Göttingen,
  Heidelberg: Springer, 1948. archive.org `in.ernet.dli.2015.7177`.
  Verwendet wurden die Abkürzungen F:, Kp und Zers.

Die Korpuswerte stammen aus dem Google Books Ngram Viewer, Korpus
„German (2019)“, 1900–2019, ohne Glättung und unter Beachtung der
Groß- und Kleinschreibung. Die relativen Häufigkeiten wurden über
1900–1924, 1925–1949, 1950–1974, 1975–1999 und 2000–2019 gemittelt und je
10⁹ Wörter angegeben. Abfragedatum: 2026-10-24.

Als heutige Bezugsquellen wurden die CLP-Verordnung (EU) Nr. 1272/2008 mit dem
deutschen Wortlaut der H- und P-Sätze, der Duden-Eintrag „Jod“, DIN 5008
für Abstände zwischen Zahlen und Einheiten sowie Abkürzungen und DIN 1310
für den Massenanteil verwendet.

### Weiterführende Literatur

Die folgenden Werke werden zur weiteren Lektüre genannt, wurden für diesen
Ratgeber aber nicht ausgewertet:

- *Organikum. Organisch-chemisches Grundpraktikum*. 1. Aufl. Anfang der
  1960er-Jahre, DDR, Autorenkollektiv; 24. Aufl. Weinheim: Wiley-VCH,
  2015.
- Gattermann, L.; Wieland, Th.: *Die Praxis des organischen Chemikers*.
  43. Aufl. Berlin: de Gruyter, 1982.
- *Houben-Weyl: Methoden der organischen Chemie*. 4. Aufl. Stuttgart:
  Thieme, ab 1952.
- Tietze, L. F.; Eicher, Th.: *Reaktionen und Synthesen im
  organisch-chemischen Praktikum und Forschungslaboratorium*. 2. Aufl.
  Stuttgart: Thieme, 1991.
