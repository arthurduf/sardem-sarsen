$graph:
- class: Workflow
  doc: Echo the command line
  id: sardem-sarsen-process
  inputs:
    input_file:
      doc: STAC Catalog
      label: catalog
      type: Directory
    s_bbox:
      doc: Bounding box
      label:  Bounding box
      type: string
  label: s expressions
  outputs:
    wf_outputs:
      outputSource:
      - step_1/outputs_result
      type: Directory[]


  steps:
    step_1:
      in:
        input_file: input_file
        s_bbox: s_bbox
      out:
      - outputs_result
      run: '#driver-command'


- baseCommand: /opt/entrypoint.sh
  class: CommandLineTool

  id: driver-command

  inputs:
    input_file:
      type: Directory
      inputBinding:
        position: 2
        prefix: --catalog_path
    s_bbox:
      type: string
      inputBinding:
        position: 1
        prefix: --s_bbox

  outputs:
    outputs_result:
      outputBinding:
        glob: /projects/data/output
      type: Directory[]
  requirements:
    EnvVarRequirement:
      envDef:
        PATH: /srv/conda/envs/env_app_snuggs/bin:/srv/conda/bin:/srv/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
    ResourceRequirement: {}
    InlineJavascriptRequirement: {}
    DockerRequirement:
      dockerPull: registry.eu-west-0.prod-cloud-ocb.orange-business.com/cloud-biomass-maap-dev/sardem_sarsen_process:1.0.0
  #stderr: std.err
  #stdout: std.out

cwlVersion: v1.0

$namespaces:
  s: https://schema.org/
s:softwareVersion: 0.3.0
schemas:
- http://schema.org/version/9.0/schemaorg-current-http.rdf 
