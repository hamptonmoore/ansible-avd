---
search:
  boost: 2
---

# EOS Designs Role Variables

## Input Variables

### Custom Templates

=== "Table"

    | Variable | Type | Required | Default | Value Restrictions | Description |
    | -------- | ---- | -------- | ------- | ------------------ | ----------- |
    | [<samp>eos_designs_custom_templates</samp>](## "eos_designs_custom_templates") | List, items: Dictionary |  |  |  |  |
    | [<samp>&nbsp;&nbsp;- template</samp>](## "eos_designs_custom_templates.[].template") | String | Required |  |  | Template file. |
    | [<samp>&nbsp;&nbsp;&nbsp;&nbsp;options</samp>](## "eos_designs_custom_templates.[].options") | Dictionary |  |  |  | Template options |
    | [<samp>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;list_merge</samp>](## "eos_designs_custom_templates.[].options.list_merge") | String |  | append_rp |  | Merge strategy for lists |
    | [<samp>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;strip_empty_keys</samp>](## "eos_designs_custom_templates.[].options.strip_empty_keys") | Boolean |  | True |  | Filter out keys from the generated output if value is null/none/undefined |

=== "YAML"

    ```yaml
    eos_designs_custom_templates:
      - template: <str>
        options:
          list_merge: <str>
          strip_empty_keys: <bool>
    ```

### Documentation Output Settings

=== "Table"

    | Variable | Type | Required | Default | Value Restrictions | Description |
    | -------- | ---- | -------- | ------- | ------------------ | ----------- |
    | [<samp>eos_designs_documentation</samp>](## "eos_designs_documentation") | Dictionary |  |  |  | Control fabric documentation generation.<br> |
    | [<samp>&nbsp;&nbsp;connected_endpoints</samp>](## "eos_designs_documentation.connected_endpoints") | Boolean |  | False |  | Generate fabric-wide documentation for connected endpoints.<br> |

=== "YAML"

    ```yaml
    eos_designs_documentation:
      connected_endpoints: <bool>
    ```

### Input Validation

=== "Table"

    | Variable | Type | Required | Default | Value Restrictions | Description |
    | -------- | ---- | -------- | ------- | ------------------ | ----------- |
    | [<samp>avd_data_conversion_mode</samp>](## "avd_data_conversion_mode") | String |  | debug | Valid Values:<br>- disabled<br>- error<br>- warning<br>- info<br>- debug<br>- quiet | Conversion Mode for AVD input data conversion.<br>Input data conversion will perform type conversion of input variables as defined in the schema.<br>The type conversion is intended to help the user to identify minor issues with the input data, while still allowing the data to be validated.<br>During conversion, messages will generated with information about the host(s) and key(s) which required conversion.<br>"disabled" means that conversion will not run - avoid this since conversion is also handling data deprecation and upgrade.<br>"error" will produce error messages and fail the task.<br>"warning" will produce warning messages.<br>"info" will produce regular log messages.<br>"debug" will produce hidden debug messages viewable with -v.<br>"quiet" will not produce any messages |
    | [<samp>avd_data_validation_mode</samp>](## "avd_data_validation_mode") | String |  | warning | Valid Values:<br>- disabled<br>- error<br>- warning<br>- info<br>- debug | Validation Mode for AVD input data validation.<br>Input data validation will validate the input variables according to the schema.<br>During validation, messages will generated with information about the host(s) and key(s) which failed validation.<br>"disabled" means that validation will not run.<br>"error" will produce error messages and fail the task.<br>"warning" will produce warning messages.<br>"info" will produce regular log messages.<br>"debug" will produce hidden debug messages viewable with -v. |

=== "YAML"

    ```yaml
    avd_data_conversion_mode: <str>
    avd_data_validation_mode: <str>
    ```