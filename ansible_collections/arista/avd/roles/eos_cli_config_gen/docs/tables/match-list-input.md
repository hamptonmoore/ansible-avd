=== "Table"

    | Variable | Type | Required | Default | Value Restrictions | Description |
    | -------- | ---- | -------- | ------- | ------------------ | ----------- |
    | [<samp>match_list_input</samp>](## "match_list_input") | Dictionary |  |  |  |  |
    | [<samp>&nbsp;&nbsp;string</samp>](## "match_list_input.string") | List, items: Dictionary |  |  |  |  |
    | [<samp>&nbsp;&nbsp;&nbsp;&nbsp;- name</samp>](## "match_list_input.string.[].name") | String | Required, Unique |  |  | Match-list Name |
    | [<samp>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;sequence_numbers</samp>](## "match_list_input.string.[].sequence_numbers") | List, items: Dictionary | Required |  |  |  |
    | [<samp>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- sequence</samp>](## "match_list_input.string.[].sequence_numbers.[].sequence") | Integer | Required, Unique |  |  | Sequence ID |
    | [<samp>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;match_regex</samp>](## "match_list_input.string.[].sequence_numbers.[].match_regex") | String | Required |  |  | Regular Expression |

=== "YAML"

    ```yaml
    match_list_input:
      string:
        - name: <str>
          sequence_numbers:
            - sequence: <int>
              match_regex: <str>
    ```
