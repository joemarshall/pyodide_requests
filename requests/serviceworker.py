import js
import json

class Worker:
    def __init__(self):
        pass

    def start_chunked_fetch(self,method,url,req_headers,req_data):
        """
            Fetch headers and chunk ID of chunked fetch
        """
        request_args={"url":url,"method":method,"req_headers":req_headers,"req_data":req_data}
        xhr=js.XMLHttpRequest.new()
        xhr.open("PUT","http://localhost:8000/fetch_service/fetch_headers",False)
        xhr.send(json.dumps(request_args))
        response=getattr(xhr,"response")
        # headers are in text as json
        headers=json.loads(response)
        id=headers["requests-fetch-id"]
        del headers["requests-fetch-id"]
        if not "content-type" in headers or headers["content-type"].startswith("text"):
            binary=False
        else:
            binary=True                                                
        return id,headers,binary

    def fetch_next_chunk(self,fetch_id,binary=False):
        xhr=js.XMLHttpRequest.new()
        xhr.open("GET",f"http://localhost:8000/fetch_service/fetch_block?{fetch_id}",False)
        if binary:
            xhr.responseType="arraybuffer"
            xhr.send()
            response=getattr(xhr,"response")
            response=response.to_py().tobytes()
        else:
            xhr.responseType="text"
            xhr.send()
            response=getattr(xhr,"response")        
        return response

_worker=Worker()


#fetch_id,headers,binary=_worker.start_chunked_fetch("GET","/files/tmp.html")
#print(headers)
#print(_worker.fetch_next_chunk(fetch_id))

class FetchStream:
    def __init__(self,method,url,headers,data,force_binary):
        self.fetch_id,self.headers,self.binary=_worker.start_chunked_fetch(method,url,req_headers=headers,req_data=data)
        if force_binary:
            self.binary=True
        self.buffer=b"" if self.binary else ""
        self.finished=False

    def get_headers(self):
        return self.headers        
        
    def read(self,count,**ignored):
        ret_val=b"" if self.binary else ""
        while not self.finished and len(ret_val)<=count:
            if len(self.buffer)>=count:
                ret_val+=self.buffer[0:count]
                self.buffer=self.buffer[count:]
            else:
                ret_val+=self.buffer
                self.buffer=_worker.fetch_next_chunk(self.fetch_id,binary=self.binary)
                if len(self.buffer)==0:
                    self.finished=True
        return ret_val

#s=FetchStream("GET","http://localhost:8000/files/tmp.html",{})
#print(s.read(1024))

