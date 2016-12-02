#!/usr/bin/env python

# MIDAS: Metagenomic Intra-species Diversity Analysis System
# Copyright (C) 2015 Stephen Nayfach
# Freely distributed under the GNU General Public License (GPLv3)

## TO DO
# -handle rna genes

import argparse, sys, os, gzip, Bio.SeqIO
from midas import utility

def read_genes(db, species_id, contigs):
	""" Read in gene coordinates from features file """
	genes_path = '%s/rep_genomes/%s/genome.features.gz' % (db, species_id)
	genes = []
	for gene in utility.parse_file(genes_path):
		if gene['gene_type'] == 'RNA':
			continue
		else:
			gene['start'] = int(gene['start'])
			gene['end'] = int(gene['end'])
			gene['seq'] = get_gene_seq(gene, contigs[gene['scaffold_id']])
			genes.append(gene)
	return genes

def read_genome(db, species_id):
	""" Read in representative genome from reference database """
	inpath = '%s/rep_genomes/%s/genome.fna.gz' % (db, species_id)
	infile = utility.iopen(inpath)
	genome = {}
	for r in Bio.SeqIO.parse(infile, 'fasta'):
		genome[r.id] = r.seq.upper()
	infile.close()
	return genome

def get_gene_seq(gene, contig):
	""" Fetch nucleotide sequence of gene from genome """
	seq = contig[gene['start']-1:gene['end']] # 2x check this works for + and - genes
	if gene['strand'] == '-':
		return(rev_comp(seq))
	else:
		return(seq)

def complement(base):
	""" Complement nucleotide """
	d = {'A':'T', 'T':'A', 'G':'C', 'C':'G'}
	if base in d: return d[base]
	else: return base

def rev_comp(seq):
	""" Reverse complement sequence """
	return(''.join([complement(base) for base in list(seq[::-1])]))

def translate(codon):
	""" Translate individual codon """
	codontable = {
	'ATA':'I', 'ATC':'I', 'ATT':'I', 'ATG':'M',
	'ACA':'T', 'ACC':'T', 'ACG':'T', 'ACT':'T',
	'AAC':'N', 'AAT':'N', 'AAA':'K', 'AAG':'K',
	'AGC':'S', 'AGT':'S', 'AGA':'R', 'AGG':'R',
	'CTA':'L', 'CTC':'L', 'CTG':'L', 'CTT':'L',
	'CCA':'P', 'CCC':'P', 'CCG':'P', 'CCT':'P',
	'CAC':'H', 'CAT':'H', 'CAA':'Q', 'CAG':'Q',
	'CGA':'R', 'CGC':'R', 'CGG':'R', 'CGT':'R',
	'GTA':'V', 'GTC':'V', 'GTG':'V', 'GTT':'V',
	'GCA':'A', 'GCC':'A', 'GCG':'A', 'GCT':'A',
	'GAC':'D', 'GAT':'D', 'GAA':'E', 'GAG':'E',
	'GGA':'G', 'GGC':'G', 'GGG':'G', 'GGT':'G',
	'TCA':'S', 'TCC':'S', 'TCG':'S', 'TCT':'S',
	'TTC':'F', 'TTT':'F', 'TTA':'L', 'TTG':'L',
	'TAC':'Y', 'TAT':'Y', 'TAA':'_', 'TAG':'_',
	'TGC':'C', 'TGT':'C', 'TGA':'_', 'TGG':'W',
	}
	return codontable[str(codon)]

def index_replace(codon, allele, pos, strand):
	""" Replace character at index i in string x with y"""
	bases = list(codon)
	bases[pos] = allele if strand == '+' else complement(allele)
	return(''.join(bases))

def fetch_ref_codon(site, gene):
	""" Fetch codon within gene for given site """
	# position of site in gene
	gene_pos = site.ref_pos-gene['start'] if gene['strand']=='+' else gene['end']-site.ref_pos
	# position of site in codon
	codon_pos = gene_pos % 3
	# gene sequence (oriented start to stop)
	ref_codon = gene['seq'][gene_pos-codon_pos:gene_pos-codon_pos+3]
	return ref_codon, codon_pos

def annotate_site(site, genes, gene_index, contigs):
	""" Annotate variant and reference site """
	# site: contains genomic position
	# genes: list of genes, each gene contains info
	# contig: contig sequence
	# gene_index: current position in list of genes; global variable
	site.snp_types = {}
	site.amino_acids = {}
	while True:
		# 1. fetch next gene
		#    if there are no more genes, snp must be non-coding so break
		if gene_index[0] < len(genes):
			gene = genes[gene_index[0]]
		else:
			site.site_type = 'NC'; site.gene_id = ''
			return
		# 2. if snp is upstream of next gene, snp must be non-coding so break
		if (site.ref_id < gene['scaffold_id'] or
		   (site.ref_id == gene['scaffold_id'] and site.ref_pos < gene['start'])):
			site.site_type = 'NC'; site.gene_id = ''
			return
		# 3. if snp is downstream of next gene, pop gene, check (1) and (2) again
		if (site.ref_id > gene['scaffold_id'] or
			 (site.ref_id == gene['scaffold_id'] and site.ref_pos > gene['end'])):
			gene_index[0] += 1
			continue
		# 4. otherwise, snp must be in gene
		#    annotate site (1D-4D) and snp (SYN, NS)
		else:
			site.gene_id = gene['gene_id']
			site.ref_codon, site.codon_pos = fetch_ref_codon(site, gene)
			if not all([_ in ['A','T','C','G'] for _ in site.ref_codon]): # check for invalid bases in codon
				site.site_type = 'NA'; site.gene_id = ''
			else:
				site.ref_aa = translate(site.ref_codon)
				for allele in ['A','T','C','G']: # + strand
					codon = index_replace(site.ref_codon, allele, site.codon_pos, gene['strand']) # +/- strand
					site.amino_acids[allele] = translate(codon)
				for allele in ['A','T','C','G']: # + strand
					alt_aa = site.amino_acids[allele]
					site.snp_types[allele] = 'SYN' if alt_aa == site.ref_aa else 'NS'
				site.site_type = str(list(site.snp_types.values()).count('SYN'))+'D'
			return







