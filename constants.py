import re

# --- CONFIGURAÇÃO GERAL (Faltava esta linha!) ---
URL_BASE = 'https://www.pciconcursos.com.br/concursos/'

# --- LISTAS DE REFERÊNCIA GEOGRÁFICA ---
UFS_SIGLAS = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
    'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC',
    'SP', 'SE', 'TO'
]

REGIOES = {
    'Norte': ['AM', 'RR', 'AP', 'PA', 'TO', 'RO', 'AC'],
    'Nordeste': ['MA', 'PI', 'CE', 'RN', 'PE', 'PB', 'SE', 'AL', 'BA'],
    'Centro-Oeste': ['MT', 'MS', 'GO', 'DF'],
    'Sudeste': ['SP', 'RJ', 'ES', 'MG'],
    'Sul': ['PR', 'RS', 'SC'],
}

# --- REGEX E PADRÕES DE EXTRAÇÃO ---
REGEX_SALARIOS = [
    r'R\$\s*([\d\.]+)(?:,\d{1,2})?',           # R$ 1.000,00 ou R$ 1.000
    r'at[eé]\s*R\$\s*([\d\.]+)(?:,\d{1,2})?',  # Até R$ ...
    r'inicial\s*R\$\s*([\d\.]+)(?:,\d{1,2})?', # Inicial R$ ...
    r'remunera[cç][aã]o\s*(?:de)?\s*R\$\s*([\d\.]+)(?:,\d{1,2})?',
    r'([\d\.]+,\d{2})\s*(?:reais|bruto|l[ií]quido)?'
]

REGEX_DATAS = [
    r'\b(\d{2}/\d{2}/\d{4})\b',     # completo
    r'\b(\d{2}/\d{2}/\d{2})\b',     # dois dígitos
    r'\b(\d{2}/\d{2})\b'            # sem ano
]

REGEX_UF = re.compile(r'\b(?:AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)\b', re.IGNORECASE)

RAW_BANCAS = """
1dn, 2dn, 3dn, 4dn, 5dn, 6dn, 7dn, 8dn, 9dn, abare, abcp, acafe, acaplam, access, acep, actio, adm&tec, advise, 
agata, agirh, agu, air, ajuri, alfa, alternative, amac, amazul, ameosc, 
amigapublica, anima, aocp, apice, aprender, ares, arespcj, aroeira, asconprev, 
asperhs, assege, assconpp, atena, auctor, avalia, avaliar, avalias, avancar, 
avancasp, avmoreira, banpara, bigadvice, biorio, bios, brb, caip, calegariox, 
carlosbittencourt, ccv, ceaf, cebraspe, cec, cefet, ceperj, cepros, ceps, 
cepuerj, cesgranrio, cespe, cetap, cetrede, cetro, cev, cfc, ciee, ciesp, 
ciscopar, cislipa, ckm, cl, click, cmm, coelhoneto, cogeps, comagsul, compec, 
comperve, comvest, concepca, coned, conesul, conpass, conscam, consel, conesp, 
consesp, consulplan, consulpam, consultec, contemax, coperve, copese, copeve, 
covest, creative, crescer, csc, ctd, cursiva, dae, darwin, decorp, dedalus, 
depsec, direcao, directa, educapb, educax, egp, ejud, ejef, epl, epbazi, esaf, 
esmarn, espm, espp, ethos, evo, exata, exatus, excelencia, exercito, fab.mil, 
facet, facto, fade, fadenor, fadesp, fadurpe, fae, faed, faepesul, faepol, 
fafipa, fama, fapec, faperp, fapeu, fastef, fat, faurgs, fcc, fcm, fcpc, fec, Fhemig, 
fema, femperj, fenaz, fenix, fepese, fesmip, fgv, fidesa, fiocruz, fip, fjpf, 
flem, fluxo, fmp, fmz, fps, framinas, fronte, fsa, fspss, fujb, fucap, fucapsul, 
fumarc, funatec, funcefet, funcepe, fundape, fundatec, fundect, fundec, fundep, 
fundepes, funece, funec, funiversa, funjab, funrio, funtef, funvapi, furb, furg, 
fuvest, gama, ganzaroli, gsa, gsassessoria, group, gualimp, hcrp, hl, iad, 
iadhed, iamspe, ian, iasp, iat, ibade, ibam, ibc, ibdo, ibec, ibeg, ibest, ibfc, 
ibgp, ibido, ibptec, icap, icece, ideap, idecan, idep, idesg, idesul, idht, idib, 
ieds, iesap, ieses, ifbaiano, ifc, iff, ifsul, igdrh, igecs, igeduc, igetec, 
imam, imagine, imparh, inaz, inqc, incp, indec, indepac, ineaa, inep, iniciativa, 
inovaty, institutomais, intec, integri, intelectus, iobv, ioplan, ipad, ipefae, 
isba, isae, iset, itame, itco, iuds, jbo, jcm, jk, jlz, jota, jvl, klc, lasalle, 
legalle, legatus, lj, magnus, makiyama, maranatha, master, maxima, mds, metodo, 
metrocapital, metropole, mgs, mouramelo, movens, mpf, mpt, msconcursos, mds, 
nc.ufpr, nbs, nce, nemesis, noroeste, nossorumo, ntcs, nubes, objetiva, officium, 
omni, omini, opgp, orhion, paqtcpb, patativa, perfas, pge, pgt, planexcon, 
planejar, policon, pontua, pr-4, pr4, prime, proam, profnit, progep, progepe, 
progesp, prograd, promun, promunicipio, publiconsult, puc, qconcursos, quadrix, 
rbo, referencia, reis, rhs, scgas, schnorr, sead, seap, secplan, seduc, segplan, 
selecon, seletiva, semasa, senai, seprod, serctam, ses, seta, shdias, sigma, 
sipros, sousandrade, spdm, srh, status, sugep, sustente, tupy, tj-ap, uece, 
ueg, uel, uem, uepb, uepa, uerj, uerr, uespi, ufabc, ufac, ufam, ufba, ufca, 
ufcg, ufersa, uff, ufgd, ufla, ufma, ufmg, ufmt, ufop, ufpa, ufpe, ufpel, ufpr, 
ufr, ufrb, ufrgs, ufrj, ufrn, ufrpe, ufrr, ufrrj, ufsba, ufsc, ufscar, ufsj, 
ufsm, uftm, ufv, una, unama, uneb, unemat, unesp, unespar, unesc, unibave, 
unicamp, unicentro, unichristus, unifal, unifap, unifase, unifei, unifesp, 
unifeso, unifil, unilab, unilavras, unimontes, unioeste, unipalmares, unirio, 
unisul, unitins, univali, univasf, univida, uniuv, uno, unoesc, upe, urca, usp, 
utfpr, verbena, vicentenelson, vunesp, wedo, wisdom, zambini
"""

TERMOS_BANCAS = [t.strip() for t in RAW_BANCAS.replace('\n', ',').split(',') if t.strip()]
REGEX_BANCAS = re.compile(r'|'.join(map(re.escape, TERMOS_BANCAS)), re.IGNORECASE)