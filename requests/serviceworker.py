import js
import json

class Worker:
    def __init__(self):
        self.direct_requests={}
        self.direct_requests_id=100000
        self.enable_direct_requests=False
        self.base_url=js.indexURL
        
    def fetch_direct(self,method,url,req_headers,req_data):
        xhr=js.XMLHttpRequest.new()
        xhr.open(method,url,False)
        for h,v in req_headers.items():
            xhr.setRequestHeader(h,v)
        xhr.responseType="arraybuffer"
        xhr.send(req_data)
        response=getattr(xhr,"response")
        if response:
            response=response.to_py().tobytes()
        else:
            response=""
        status=xhr.status
        reason=xhr.statusText
        header_string=xhr.getAllResponseHeaders()
        headers={}
        for line in header_string.splitlines():
            splits=line.split(":")
            header_name=splits[0]
            if len(splits)>1:
                header_value=":".join(splits[1:])
            headers[header_name]=header_value
        if not "content-type" in headers or headers["content-type"].startswith("text"):
            binary=False
        else:
            binary=True                                                
        id =self.direct_requests_id
        self.direct_requests[id]=response
        self.direct_requests_id+=1
        return id,headers,status,reason,binary
        

    def start_chunked_fetch(self,method,url,req_headers,req_data):
        """
            Fetch headers and chunk ID of chunked fetch
        """
        if self.enable_direct_requests:
            return self.fetch_direct(method,url,req_headers,req_data)
        request_args={"url":url,"method":method,"req_headers":req_headers,"req_data":req_data}
        xhr=js.XMLHttpRequest.new()
        xhr.open("PUT",f"{self.base_url}/fetch_service/fetch_headers",False)
        xhr.send(json.dumps(request_args))
        if int(xhr.status /100)!=2:
            # couldn't contact service worker
            # do direct fetch instead
            # this happens in incognito windows
            self.enable_direct_requests=True
            return self.fetch_direct(method,url,req_headers,req_data)
        response=getattr(xhr,"response")
        # headers are in text as json
        headers=json.loads(response)
        id=headers["requests-fetch-id"]
        del headers["requests-fetch-id"]
        status=headers["requests-fetch-status"]
        del headers["requests-fetch-status"]
        reason=headers["requests-fetch-status-text"]
        del headers["requests-fetch-status-text"]
        if not "content-type" in headers or headers["content-type"].startswith("text"):
            binary=False
        else:
            binary=True                                                
        return id,headers,status,reason,binary

    def fetch_next_chunk(self,fetch_id,binary=False):        
        if fetch_id in self.direct_requests:
            chunk_data=self.direct_requests[fetch_id]
            if chunk_data==b"":
                # end of request
                del self.direct_requests[fetch_id]
            else:
                self.direct_requests[fetch_id]=b""
            return chunk_data
        xhr=js.XMLHttpRequest.new()
        xhr.open("GET",f"{self.base_url}/fetch_service/fetch_block?{fetch_id}",False)
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
        self.fetch_id,self.headers,self.status,self.reason,self.binary=_worker.start_chunked_fetch(method,url,req_headers=headers,req_data=data)
        if force_binary:
            self.binary=True
        self.buffer=b"" if self.binary else ""
        self.finished=False if self.status//100==2 else True

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

