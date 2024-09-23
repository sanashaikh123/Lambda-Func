import base64
import json
import ast
#print('Loading function')


# event['records'] - The data related one namespace / service : AWS/EC2 or ....


def lambda_handler(event,context):
    output = []
    
    for record in event['records']:
        payload = base64.b64decode(record['data']).decode('utf-8')
        
        payload2 = payload.split('\n')[:-1]
        #print(payload2,type(payload2))
        
        req_out = []
        for item in payload2:
            payload3 = json.loads(item)
            req_out.append(payload3)
        #print(req_out)
        
        updated_payload = ''
        

        for item in req_out:
        
        # Do the item processing over here & add it to the updated payload
            temp_dct = item['dimensions']
            #
            del item['dimensions']
        
            for k, v in temp_dct.items():
                
                item1 = item.copy()
                
                item1['dimension'] = k
                item1['dimension_value'] = v
                item1['add_info'] = "region="+item1['region']+";!@#;account_id="+item1['account_id']+";!@#;"+item1['dimension']+"="+item1['dimension_value']
                item1['source_host'] = item1['dimension_value'] + ":" + item1['region'] + ":" + item1['namespace'] + ":" + item1['account_id']
                item1['counter'] = item1['metric_name']
                item1['object'] = item1['namespace']
                item1['instance'] = v
                
                misc_data = "Additional Information"
                #output1 = 'time={time},dimension={dimension},dimension_value={dimension_value},Value={value},name_space={name_space},add_info="{add_info}",instance={instance},source_host={source_host},counter={counter},object={object}\n'.format(
                    #time=item1['timestamp'], dimension=item1['dimension'], dimension_value=item1['dimension_value'],
                    #counter=item1['metric_name'], value=item1['value'], name_space=item1['namespace'],
                    #add_info=misc_data,
                    #instance=item1['dimension_value'], source_host=item1['source_host'], object=item1['namespace'])
                
                updated_payload.append(item1)
             
        output_record = {
            'recordId': record['recordId'],
            'result': 'Ok',
            'data': base64.b64encode(updated_payload.encode('utf-8')).decode('utf-8')
            
        }
        output.append(output_record)
    
    
    return {'records': output}
    