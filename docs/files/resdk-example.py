from resdk import Resolwe
res = Resolwe('admin', 'admin', 'https://torta.bcm.genialis.com')

# Recomended: start logging
resdk.start_logging()

sample = res.sample.get(1)
sample.download(type='bam')

samples = res.sample.filter(descriptor__organism="Homo sapiens")
for sample in samples:
    sample.download(type='bam')

sample = res.sample.get(1)
for data_id in sample.data:
    data = res.data.get(data_id)
    print data.process_name

rose2_list = res.data.filter(type='data:chipseq:rose2:')
rose2 = rose2_list[0]
rose2.download(name='20150531-u266-A-H3K27Ac-ML1949_S2_R1_mapped_peaks_Plot_panel.png')

genome = res.data.get('hg19')
genome_id = genome.id
reads_id = sample.data[0]
aligned = res.run('alignment-bowtie-2-2-3_trim', input={
                      'genome': genome_id,
                      'reads': reads_id,
                      'reporting': {'rep_mode': 'k', 'k_reports': 1}
                  })
aligned.status

aligned.update()
aligned.status
