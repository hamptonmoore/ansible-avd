=== "Table"

    | Variable | Type | Required | Default | Value Restrictions | Description |
    | -------- | ---- | -------- | ------- | ------------------ | ----------- |
    | [<samp>underlay_ospf_area</samp>](## "underlay_ospf_area") | String |  | `0.0.0.0` | Format: ipv4 |  |
    | [<samp>underlay_ospf_bfd_enable</samp>](## "underlay_ospf_bfd_enable") | Boolean |  | `False` |  |  |
    | [<samp>underlay_ospf_max_lsa</samp>](## "underlay_ospf_max_lsa") | Integer |  | `12000` |  |  |
    | [<samp>underlay_ospf_process_id</samp>](## "underlay_ospf_process_id") | Integer |  | `100` |  |  |

=== "YAML"

    ```yaml
    underlay_ospf_area: <str>
    underlay_ospf_bfd_enable: <bool>
    underlay_ospf_max_lsa: <int>
    underlay_ospf_process_id: <int>
    ```
