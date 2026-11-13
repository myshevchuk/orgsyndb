# Die Produktionsplanung verstehen

Die Prognose hilft Ihnen zu entscheiden, wann Sie Gebinde aus Bulk
abfüllen, wann Sie eine Synthese beginnen und wie viel sie liefern muss.
Bulk ist Material, das in Chargen zum Abfüllen bereitliegt. Die Prognose
ersetzt eine persönliche Einschätzung der Dringlichkeit durch dieselbe
Berechnung für alle. Bestand, Bedarf, Synthesedauer und die Annahmen hinter
dem Ergebnis bleiben sichtbar.

Die englische Fassung ist [PLANNING.md](PLANNING.md).

## Die Zahlen hinter einer Priorität finden

Öffnen Sie **Planung** zwischen **Bestand** und **Aufgaben** in der
Navigation. Die Liste zeigt Artikel mit hoher oder mittlerer Priorität
und Artikel, bei denen eine Maßnahme ansteht. Der kleinste **Spielraum**
steht zuerst: Das ist die Zeit, die bis zum nötigen Beginn einer neuen
Synthese bleibt. Mit **Alle Artikel** sehen Sie jeden Artikel mit einer
Prognose.

Ein *Artikel* fasst alle Gebindegrößen mit derselben Artikelnummer
zusammen. Jede Größe hat ihren eigenen Bestand und Bedarf. Folgen Sie
einer Gebindegröße zur Bestandsseite und dort zum Abschnitt **Prognose**,
um die Berechnungsgrundlage zu sehen. Auch die Aufgabenseite zeigt die
Prognose für ihr Produkt.

Die Zeile über der Planungstabelle nennt die aktuell geltenden Parameter.
Die Vorgabewerte in dieser Anleitung gelten, solange das Personal sie
nicht geändert hat.

## Wie die Anwendung den Bedarf schätzt

Die Prognose verwendet die im Bestand erfassten Lieferungen als Verbrauch.
Sie betrachtet standardmäßig die letzten zwölf vollständigen Quartale.
Ein Quartal umfasst drei Monate. Quartale vor den ersten erfassten Daten
bleiben außen vor. Das aktuelle, unvollständige Quartal geht nicht in die
Bedarfsschätzung ein.

Die Anwendung wählt zwischen zwei *Bedarfsmodellen*: zwei Arten zu
beschreiben, wie viele Gebinde künftige Lieferungen benötigen können.

### Wenn genügend einzelne Aufträge vorliegen

Das **Auftragsmodell** verwendet datierte Lieferscheinpositionen mit der
jeweiligen Anzahl gelieferter Gebinde. Es braucht standardmäßig mindestens
sechs Aufträge. Diese müssen im betrachteten Zeitraum liegen, in Quartalen
nach dem letzten Quartal mit einer manuell eingetragenen Verbrauchssumme.
Ohne eingetragene Summe steht der ganze betrachtete Zeitraum zur Verfügung.

Die Berechnung verwendet die Häufigkeit und die bisherigen Größen der
Aufträge. Sie vergleicht die Auftragshäufigkeit im verfügbaren Zeitraum
mit der in dessen letzten vier Quartalen und nimmt den höheren Wert. Bei
weniger als vier Quartalen verwendet sie alle verfügbaren Quartale. So
geht ein zuletzt gestiegener Bedarf ein, ohne darauf zu warten, dass die
älteren Daten aufholen.

Das Modell nimmt an, dass künftige Aufträge unabhängig voneinander mit
dieser Häufigkeit eintreffen. Für jeden Auftrag nimmt es eine zufällig aus
den bisherigen Aufträgen gezogene Größe an. Die Anwendung berechnet die
Wahrscheinlichkeit, dass der Bestand ihren gesamten Bedarf deckt. Für
diese Annahmen ist die Wahrscheinlichkeitsberechnung exakt.

Auf der Seite bedeutet **λ** Aufträge je Tag. Der **Median** der
Auftragsgrößen ist die mittlere Größe, wenn Sie die bisherigen Aufträge
nach Größe sortieren, oder der Mittelwert der beiden mittleren Größen.
Die Seite nennt außerdem die Zahl der Aufträge und den größten Auftrag.

Sie können dem Modell mehr Historie geben, indem Sie alte
Papierlieferscheine als **nachgetragen – Bestand bleibt unverändert**
erfassen. Diese historischen Lieferscheine gehen in den Bedarf ein, ohne
den heutigen Bestand zu ändern.

### Wenn zu wenige einzelne Aufträge vorliegen

Das **Quartalsmodell** verwendet stattdessen die Verbrauchssummen je
Quartal. Es vergleicht den Durchschnitt des betrachteten Zeitraums mit
dem der letzten vier Quartale und nimmt den höheren Wert. Es
berücksichtigt auch, wie stark die Quartalssummen schwanken.

Auf der Seite ist **m** die durchschnittliche Zahl von Gebinden je Quartal,
die die Prognose verwendet. **v** misst die Schwankung zwischen den
Quartalen. Die Berechnung setzt v mindestens so hoch wie m an. Gleiche
bisherige Quartalssummen führen dadurch nicht dazu, dass die Prognose
einen vollkommen gleichmäßigen Bedarf annimmt.

Zahlen aus diesem Modell tragen die Kennzeichnung **grob**. Quartalssummen
sagen der Anwendung nicht, wann einzelne Aufträge eingingen oder wie groß
sie waren. Die angegebene Sicherheit dieser Näherung gilt daher nur
annähernd. Verwendet eine Größe dieses Modell, ist auch die Prognose des
Artikels als grob gekennzeichnet.

Für einen Eintrag ohne Verbrauch im betrachteten Zeitraum gibt es keine
Prognose. Seine Seite zeigt **Kein Verbrauch, keine Prognose.** Fehlende
Historie belegt nicht, dass der Bestand unbegrenzt reicht.

**Bedarf/Jahr** zeigt den vom Modell erwarteten Jahresverbrauch in
Gebinden, getrennt für jede Größe.

## Reichweite als Zeit bei einer gewählten Sicherheit lesen

Die **Reichweite** gibt an, wie viele Tage der Bestand den vorhergesagten
Bedarf bei der gewählten **Sicherheit** deckt. Die Vorgabe ist 95 %: Unter
den Annahmen des Modells deckt der Bestand den Bedarf dieses Zeitraums
mit mindestens 95 % Wahrscheinlichkeit. Eine höhere Sicherheit verlangt
für denselben Zeitraum mehr Bestand und verkürzt die Reichweite des
vorhandenen Bestands.

Große, gelegentliche Aufträge sind dabei entscheidend. Angenommen, etwa
einmal pro Quartal kommt ein Auftrag über zehn Gebinde, und Sie haben neun.
Den nächsten Auftrag können Sie nicht decken. Bei 95 % Sicherheit ergibt
das Auftragsmodell eine Reichweite von **4 Tagen**. Eine grobe Berechnung
aus den Quartalssummen derselben Historie ergibt **47 Tage**. Der
durchschnittliche Verbrauch allein verbirgt das Risiko eines großen
Einzelauftrags.

Im Auftragsmodell kann selbst ein Bestand von null eine kurze positive
Reichweite haben. Das ist der Zeitraum, in dem mit der gewählten Sicherheit
kein Auftrag eintrifft. Es bedeutet nicht, dass Gebinde vorhanden sind;
der Bestand bleibt als aufgebraucht gekennzeichnet.

### Mehrere Größen teilen sich einen Bulk-Vorrat

Die **Reichweite des Bestands** verwendet nur die abgefüllten Gebinde
dieser Größe. Die Reichweite des Artikels berücksichtigt auch nutzbares
Bulk.

Eine Synthese ergänzt das Bulk des Artikels, das allen Größen zur
Verfügung steht. Die Berechnung verwendet zuerst die abgefüllten Gebinde
jeder Größe. Dann ermittelt sie, wie das gemeinsame Bulk die fehlenden
Gebinde decken kann, damit jede Größe für denselben Zeitraum reicht. Das
Bulk zählt dabei einmal.

Damit alle Größen zusammen bei 95 % gedeckt sind, verwendet die Berechnung
für jede Größe mit Bedarf eine höhere Sicherheit. Bei zwei Größen sind es
**97,5 % je Größe**. Allgemein verteilt sie das zugelassene Risiko von 5 %
auf die Größen. Deshalb kann sich die Sicherheit einer Größe in der
Artikelberechnung von ihrer Sicherheit unter Reichweite des Bestands
unterscheiden.

### Warum nutzbares Bulk kleiner als die erfasste Menge ist

**Nutzbares Bulk** berücksichtigt, dass Sie ganze Gebinde aus getrennten
Chargen abfüllen. Von jeder offenen Charge zieht die Berechnung die größte
Gebindegröße des Artikels unter den Größen mit Bedarf ab. Eine kleinere
Charge trägt null bei. Auch fehlende Gebinde rundet die Berechnung auf
ganze Gebinde auf.

Bei Größen von 10 mg und 20 mg und einer Charge mit 360 mg zählt die
Prognose zum Beispiel **340 mg** als nutzbares Bulk. Ohne abgefüllte
Gebinde und bei einem Quartalsbedarf von neun Gebinden je Größe in jedem
von zwölf Quartalen beträgt die Reichweite des Artikels bei der
vorgegebenen Sicherheit **62 Tage**. Würde jede Größe die ganze Charge
erhalten, würde dasselbe Material doppelt zählen.

Zwei getrennte Chargen mit je 6 mg können kein Gebinde von 10 mg füllen.
Ihre zusammen 12 mg tragen deshalb **null nutzbares Bulk** zu diesem
Artikel bei.

Für die Umrechnung zwischen mg und µmol braucht die Anwendung die molare
Masse der Verbindung. Eine nicht umrechenbare Charge zählt nicht zum
nutzbaren Bulk und löst **Bulk prüfen** aus. Eine nicht umrechenbare
Gebindegröße ist auf ihre eigenen abgefüllten Gebinde angewiesen und kann
die Reichweite des Artikels begrenzen.

## Ermitteln, wann die Synthese beginnen muss

Die **Synthesedauer** ist die längste Dauer der letzten drei
abgeschlossenen Synthesen des Artikels. Verworfene Aufgaben zählen nicht.
Bis drei abgeschlossene Synthesen vorliegen, berücksichtigt die Berechnung
auch die Vorgabe von 21 Tagen. Eine abgeschlossene Synthese mit zehn Tagen
ergibt daher weiterhin eine Schätzung von 21 Tagen; eine längere erfasste
Synthese kann sie erhöhen.

Der **Puffer** ist die Zeit zwischen dem Ende der Synthese und der
Lieferbereitschaft des Produkts. Er berücksichtigt die Qualitätskontrolle
(QC), das Abfüllen und Unvorhergesehenes. Die Vorgabe ist 28 Tage.

Die Berechnung zieht beide Zeiten von der Reichweite ab:

**Spielraum = Reichweite − Puffer − Synthesedauer.**

Der Spielraum gibt an, wie viele Tage bis zum nötigen Beginn einer neuen
Synthese bleiben. **Spätester Start** ist heute plus dieser Spielraum. Bei
negativem Spielraum liegt der späteste Start in der Vergangenheit: Ein
Beginn heute ließe unter den Annahmen der Prognose bereits zu wenig Zeit.

Die Priorität folgt aus dem Spielraum. Mit den Vorgabewerten gilt:

| Spielraum | Priorität |
| --- | --- |
| Weniger als 14 Tage, einschließlich negativer Werte | hoch |
| Mindestens 14 Tage, weniger als 56 Tage | mittel |
| Mindestens 56 Tage | niedrig |

Ein Artikel mit zehn Gebinden zu 1 mg, ohne Bulk und mit einem
Quartalsverbrauch von neun Gebinden in jedem von zwölf Quartalen hat
beispielsweise eine angezeigte Reichweite von 60 Tagen. Mit vorgegebener
Synthesedauer und Puffer beträgt sein Spielraum 11 Tage; seine Priorität
ist hoch.

Die Anzeige rundet Reichweite und Spielraum auf ganze Tage ab. Auch der
späteste Start verwendet den abgerundeten Spielraum. Für die
Prioritätsgrenzen zählen die Werte vor der Rundung.

## Prüfen, ob eine laufende Aufgabe rechtzeitig fertig wird

Die Priorität des Artikels beantwortet, wie dringend eine **neue Synthese**
nötig ist. Sie verwendet weiterhin die volle Synthesedauer, auch wenn
bereits Arbeit läuft. Die Planungsliste zeigt daneben geplante und
laufende Aufgaben mit ihrem voraussichtlichen Ende.

Der eigene Spielraum einer Aufgabe beantwortet, ob **diese Aufgabe** das
Produkt rechtzeitig bereitstellen kann. Eine geplante Aufgabe braucht die
volle Synthesedauer. Eine laufende Aufgabe braucht nur die geschätzte
Synthesedauer abzüglich der Tage seit ihrem Beginn, mindestens null. Ihr
voraussichtliches Ende ist heute plus diese Restzeit.

Der Spielraum der Aufgabe ist Reichweite minus Puffer minus ihre Restzeit.
Im Beispiel oben hat eine vor 14 Tagen begonnene Synthese einen eigenen
Spielraum von **25 Tagen** und mittlere Priorität. Der Artikel behält die
hohe Priorität. Die beiden Prioritäten beantworten unterschiedliche Fragen.

Unter null ist der eigene Spielraum der Aufgabe als **verspätet**
gekennzeichnet. Die geschätzte Restarbeit und der Puffer passen dann nicht
mehr in die Reichweite.

Bei geplanten und laufenden Aufgaben mit passender Prognose verwendet die
Anwendung diese Priorität überall, wo sie Aufgaben anzeigt, sortiert oder
filtert. Sie kennzeichnet sie als **berechnet**; wenn Sie auf die
Priorität zeigen, sehen Sie den Spielraum in Tagen. Alle anderen
Aufgaben, auch abgeschlossene und verworfene, behalten die im Formular
eingetragene Priorität mit der Kennzeichnung **manuell**. Sie können eine
berechnete Priorität nicht durch Ändern dieses Feldes überschreiben.

Eine Aufgabe passt zum Artikel ihrer Substanz, sofern die Substanz einen
Artikel hat. Sie passt damit zu höchstens einem Artikel. Ein Artikel ohne
Artikelnummer hat keinen Verbrauch und keine Prognose. Aufgaben, die zu
ihm passen, zeigen ihre eingetragene Priorität.

## Die nächste Maßnahme wählen

Die Spalte **Maßnahmen** bietet die Aktionen an, deren Bedingungen
zutreffen:

| Maßnahme | Warum sie erscheint und was sie öffnet |
| --- | --- |
| **Abfüllen** mit einer Größe | Die abgefüllten Gebinde dieser Größe reichen kürzer als der Puffer, und die offenen Chargen können mindestens ein Gebinde füllen. Öffnen Sie das Abfüllformular für diese Größe. |
| **Bulk prüfen** | Eine offene Charge lässt sich wegen fehlender molarer Masse nicht umrechnen. Öffnen Sie die Bulk-Liste zur Prüfung; die Charge könnte genug Material enthalten, um eine Synthese zu vermeiden. |
| **Synthese planen** | Die Priorität ist hoch oder mittel, keine passende Aufgabe ist geplant oder läuft, und alle offenen Chargen des Artikels lassen sich umrechnen. Öffnen Sie eine neue Aufgabe mit ausgefülltem Substanzschlüssel sowie Syntheseweg und vorgeschlagener Anfangsstufe, wenn ein Syntheseweg diese Substanz herstellt. |

Ein *Syntheseweg* ist eine geordnete Folge von Synthesestufen. Für jeden
Syntheseweg in der Sammlung, der die Substanz des Artikels herstellt und
nicht zurückgezogen ist, heißt die Maßnahme **Synthese planen über
&lt;ID&gt;**. Die Maßnahmen erscheinen nach Syntheseweg-ID sortiert. Wenn
kein Syntheseweg die Substanz herstellt, bleibt es bei **Synthese planen**;
dann ist nur der Substanzschlüssel ausgefüllt.

Um Arbeit zu überspringen, deren Produkt bereits vorrätig ist, schlägt
die Planung die späteste Stufe vor, für deren vorangehende Stufe das
*Zwischenprodukt* in einer offenen Charge vorliegt. Das Zwischenprodukt
ist das erste Produkt einer Stufe, das die nächste Stufe als Substrat
einsetzt. Eine offene Charge hat eine Menge über null; hergestellte und
gekaufte Chargen zählen gleichermaßen. Ist keines dieser Zwischenprodukte
vorrätig, schlägt die Planung Stufe 1 vor. Bei einer späteren Stufe ergänzt
die Maßnahme **ab Stufe &lt;k&gt;, &lt;name&gt; vorrätig** und nennt damit
das Zwischenprodukt.

Die Planung reserviert nichts und prüft nicht, ob die Menge ausreicht.
Prüfen Sie die Menge und bestätigen oder ändern Sie **Beginn ab Stufe**
im Aufgabenformular. Der Syntheseweg der Aufgabe muss deren Substanz
herstellen; die Stufen der Aufgabe beginnen bei der gewählten Stufe.
Das Überspringen von Stufen verkürzt die Synthesedauer der Prognose nicht.

Synthese planen ist ein Link, wenn Sie angemeldet sind, sonst reiner Text.
Nach dem Speichern erscheint die neue Aufgabe beim Artikel. Solange die
Aufgabe geplant ist oder läuft, entfällt diese Maßnahme.

### Wie viel eine neue Synthese liefern muss

**Neue Synthese** in der Prognose des Bestandseintrags nennt die zusätzliche
Materialmenge, die diesen Zeitraum decken muss:

**Synthesedauer + Puffer + Zielreichweite.**

Die Zielreichweite beträgt standardmäßig 365 Tage. Die Berechnung
verwendet dieselbe Sicherheit je Größe wie die Reichweite des Artikels.
Sie zieht vorhandene abgefüllte Gebinde und nutzbares Bulk ab und rundet
die fehlende Materialmenge auf ganze mg oder µmol auf. Eine Menge in µmol
erscheint zusätzlich in mg. Lässt sich eine Größe nicht umrechnen, erscheint
ihre fehlende Menge als Anzahl ihrer eigenen Gebinde.

Nach dem Ende einer Synthese können angemeldete Personen auf einer Aufgabe
mit Charge und passendem Artikel **Als Bulk erfassen** verwenden. Das
öffnet eine neue Charge mit ausgefülltem Artikel, Chargenbezeichnung und
Enddatum. Tragen Sie die Menge ein und speichern Sie. Aufgaben- und
Bulk-Seiten verknüpfen Einträge mit derselben Chargenbezeichnung nur dann,
wenn auch ihre Artikel passen.

## Den Lieferrhythmus lesen

Der **Lieferrhythmus** des Bestandseintrags zeigt die letzte Lieferung und
die Zahl der Lieferungen in den letzten 365 Tagen. Mit mindestens drei
Lieferscheinen in den letzten 730 Tagen zeigt er auch das **Übliche
Intervall**. Das ist der Median der Abstände zwischen aufeinanderfolgenden
Lieferungen, auf ganze Tage gerundet.

**Nächste Lieferung erwartet** addiert dieses Intervall zum Datum der
letzten Lieferung. Es beschreibt den erfassten Rhythmus und sagt keinen
nächsten Auftrag eines bestimmten Kunden vorher. Stornierte Lieferungen
und stornierte nachgetragene Lieferscheine zählen nicht.

## Wer die Annahmen ändert

Personal mit Zugang zur Verwaltung ändert einen gemeinsamen Datensatz
**Planungsparameter** unter `/lab/admin/planning/parameters/`. Seine
Änderungshistorie hält Änderungen der Annahmen fest. Die Planungsseite
zeigt die verwendeten Werte. Ohne gespeicherten Datensatz gelten die
Vorgabewerte.

| Parameter | Vorgabe | Erlaubte Werte |
| --- | --- | --- |
| Sicherheit | 95 % | 50–99,9 % |
| Puffer in Tagen | 28 | 0–365 |
| Synthesedauer ohne Historie in Tagen | 21 | 1–730 |
| Historie in Quartalen | 12 | 4–40 |
| Mindestzahl der Aufträge | 6 | 3–100 |
| Hohe Priorität unter Tagen Spielraum | 14 | Mindestens 0; unter der Grenze für mittel |
| Mittlere Priorität unter Tagen Spielraum | 56 | Über der Grenze für hoch |
| Zielreichweite in Tagen | 365 | 30–1095 |

## Was die Prognose nicht sagen kann

Die Prognose hängt von der eingetragenen Historie ab. Das Auftragsmodell
nimmt unabhängige Aufträge mit gleichbleibender Häufigkeit an. Ein Trend
zeigt sich nur durch den Vergleich mit der jüngeren Häufigkeit. Keines der
Modelle berücksichtigt Jahreszeiten oder sagt Aufträge einzelner Kunden
vorher.

Bei wenigen Aufträgen geben die bisherigen Auftragsgrößen nur ein
begrenztes Bild künftiger Größen. Das Quartalsmodell bleibt grob. Die
gemeinsame Absicherung mehrerer Größen kann die Schätzung großzügig
machen, besonders bei vielen Größen und großen, gelegentlichen Aufträgen.
Auch die zuerst erfassten Synthesedauern können ungewöhnlich sein; die
Vorgabe zählt weiter mit, bis drei abgeschlossene Synthesen vorliegen.

Die Prognose plant weder Personen noch Geräte ein und verschickt keine
Benachrichtigungen. Sie lässt die bestehenden Bestandsstufen unverändert.
Entscheiden Sie anhand der Zahlen und ihrer Grundlage, was Ihre
Aufmerksamkeit braucht; eine angezeigte Sicherheit hängt von den Annahmen
des Modells und der Qualität der erfassten Daten ab.
